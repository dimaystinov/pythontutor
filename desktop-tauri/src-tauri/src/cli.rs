//! Optional, pinned OpenCode installation. Downloads only after an explicit install command.
use serde::Deserialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{fs, io::{Read, Write}, path::{Path, PathBuf}, sync::atomic::{AtomicBool, Ordering}, time::Duration};
use tauri::{Emitter, Manager, State};
static BUSY: AtomicBool = AtomicBool::new(false);
static CANCEL: AtomicBool = AtomicBool::new(false);
const VERSION: &str = "1.19.0";
#[derive(Deserialize)]
struct Asset { url: String, digest: String, size: u64 }
fn asset() -> Result<Asset, String> {
    let key = if cfg!(windows) { "opencode-windows-x64-baseline.zip" }
      else if cfg!(target_arch="aarch64") { "opencode-darwin-arm64.zip" }
      else { "opencode-darwin-x64-baseline.zip" };
    serde_json::from_str::<std::collections::HashMap<String,Asset>>(include_str!("../../opencode.json"))
        .map_err(|e|e.to_string())?.remove(key).ok_or("Нет установщика для этой системы.".into())
}
fn name() -> &'static str { if cfg!(windows) {"opencode.exe"} else {"opencode"} }
fn directory(app: &tauri::AppHandle) -> Result<PathBuf,String> {
    Ok(app.path().app_data_dir().map_err(|e|e.to_string())?.join("opencode").join(VERSION))
}
fn hash(path: &Path) -> Result<String,String> {
    let mut f=fs::File::open(path).map_err(|e|e.to_string())?;
    let mut h=Sha256::new();let mut buf=vec![0;1024*1024];
    loop {let n=f.read(&mut buf).map_err(|e|e.to_string())?;if n==0 {break;}h.update(&buf[..n]);}
    Ok(format!("{:x}",h.finalize()))
}
fn ready(dir: &Path) -> bool {dir.join(name()).is_file() && dir.join("verified.sha256").is_file()}
pub fn path(app: &tauri::AppHandle) -> Result<PathBuf,String> {
    let dir=directory(app)?;
    if !ready(&dir) {return Err("Установите помощника OpenCode кнопкой в его окне.".into());}
    let binary=dir.join(name());
    if hash(&binary)?!=fs::read_to_string(dir.join("verified.sha256")).map_err(|e|e.to_string())? {
        return Err("Файлы помощника повреждены. Установите его заново.".into());
    }
    Ok(binary)
}
#[tauri::command]
pub fn cli_status(app: tauri::AppHandle) -> Result<Value,String> {
    Ok(json!({"installed":path(&app).is_ok(),"bytes":asset()?.size,"version":VERSION}))
}
#[tauri::command]
pub fn cancel_cli_install() {CANCEL.store(true,Ordering::Relaxed);}
fn active() -> Result<(),String> {if CANCEL.load(Ordering::Relaxed){Err("Загрузка отменена.".into())}else{Ok(())}}
fn unpack(archive: &Path, destination: &Path) -> Result<(),String> {
    let mut z=zip::ZipArchive::new(fs::File::open(archive).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    let candidates:Vec<usize>=(0..z.len()).filter(|&i|z.by_index(i).map(|e|Path::new(e.name()).file_name()==Some(std::ffi::OsStr::new(name()))).unwrap_or(false)).collect();
    if candidates.len()!=1 {return Err("В архиве нет единственного файла OpenCode.".into());}
    let mut entry=z.by_index(candidates[0]).map_err(|e|e.to_string())?;
    if entry.is_dir() || entry.size()>512*1024*1024 {return Err("Некорректный файл OpenCode.".into());}
    // Never use an archive-supplied path for the destination.
    let mut out=fs::File::create(destination).map_err(|e|e.to_string())?;
    std::io::copy(&mut entry,&mut out).map_err(|e|e.to_string())?;
    out.sync_all().map_err(|e|e.to_string())?;
    #[cfg(unix)] {use std::os::unix::fs::PermissionsExt;fs::set_permissions(destination,fs::Permissions::from_mode(0o755)).map_err(|e|e.to_string())?;}
    Ok(())
}
fn install(app: tauri::AppHandle) -> Result<(),String> {
    if path(&app).is_ok(){return Ok(());}
    let a=asset()?;let dir=directory(&app)?;let parent=dir.parent().unwrap();
    fs::create_dir_all(parent).map_err(|e|e.to_string())?;
    let tmp=tempfile::tempdir_in(parent).map_err(|e|e.to_string())?;
    let archive=tmp.path().join("download.zip");
    let client=reqwest::blocking::Client::builder().connect_timeout(Duration::from_secs(15)).timeout(Duration::from_secs(600)).build().map_err(|e|e.to_string())?;
    let mut response=client.get(&a.url).send().and_then(|r|r.error_for_status()).map_err(|e|format!("Не удалось скачать помощника: {e}"))?;
    let mut out=fs::File::create(&archive).map_err(|e|e.to_string())?;
    let mut h=Sha256::new();let mut total=0u64;let mut buf=vec![0;256*1024];let mut last=101;
    loop {active()?;let n=response.read(&mut buf).map_err(|e|e.to_string())?;if n==0{break;}total+=n as u64;
        if total>a.size{return Err("Неверный размер загрузки.".into());}
        out.write_all(&buf[..n]).map_err(|e|e.to_string())?;h.update(&buf[..n]);
        let percent=total*100/a.size;if percent!=last {let _=app.emit("cli-install-progress",json!({"percent":percent,"text":format!("Скачивание · {percent}%")}));last=percent;}
    }
    drop(out);
    if total!=a.size || format!("sha256:{:x}",h.finalize())!=a.digest{return Err("Проверка файла не пройдена. Повторите загрузку.".into());}
    active()?;let _=app.emit("cli-install-progress",json!({"percent":100,"text":"Проверка и установка…"}));
    let binary=tmp.path().join(name());unpack(&archive,&binary)?;
    fs::write(tmp.path().join("verified.sha256"),hash(&binary)?).map_err(|e|e.to_string())?;
    fs::remove_file(&archive).map_err(|e|e.to_string())?;active()?;
    // Replace only this app's managed version, after the complete new copy is verified.
    if dir.exists(){fs::remove_dir_all(&dir).map_err(|e|e.to_string())?;}
    fs::rename(tmp.path(),&dir).map_err(|e|e.to_string())?;
    Ok(())
}
#[tauri::command]
pub async fn install_cli(app: tauri::AppHandle,state:State<'_,crate::AppState>,profile:String)->Result<(),String>{
    drop(state.checked(&profile)?);
    if BUSY.swap(true,Ordering::SeqCst){return Err("Помощник уже скачивается.".into());}
    CANCEL.store(false,Ordering::Relaxed);
    let result=tauri::async_runtime::spawn_blocking(move||install(app)).await.map_err(|e|e.to_string()).and_then(|r|r);
    BUSY.store(false,Ordering::SeqCst);result
}
#[cfg(test)]mod tests{
 use super::*;
 #[test]fn pinned_assets(){let a=asset().unwrap();assert!(a.url.starts_with("https://github.com/anomalyco/opencode/releases/download/v1.19.0/"));assert!(a.size>40_000_000);assert_eq!(a.digest.len(),71);}
 #[test]fn missing_install_is_not_ready(){let d=tempfile::tempdir().unwrap();assert!(!ready(d.path()));fs::write(d.path().join(name()),b"partial").unwrap();assert!(!ready(d.path()));}
 #[test]fn archive_cannot_choose_output_path(){let d=tempfile::tempdir().unwrap();let archive=d.path().join("test.zip");let mut z=zip::ZipWriter::new(fs::File::create(&archive).unwrap());z.start_file(format!("../../{}",name()),zip::write::SimpleFileOptions::default()).unwrap();z.write_all(b"verified executable fixture").unwrap();z.finish().unwrap();let target=d.path().join("safe");unpack(&archive,&target).unwrap();assert_eq!(fs::read(target).unwrap(),b"verified executable fixture");}
 #[test]
 #[ignore = "requires an official archive supplied by OPENCODE_TEST_ARCHIVE"]
 fn official_archive_runs_after_verification(){
  let archive=PathBuf::from(std::env::var("OPENCODE_TEST_ARCHIVE").expect("archive required"));let a=asset().unwrap();
  assert_eq!(fs::metadata(&archive).unwrap().len(),a.size);
  assert_eq!(format!("sha256:{}",hash(&archive).unwrap()),a.digest);
  let dir=tempfile::tempdir().unwrap();let binary=dir.path().join(name());unpack(&archive,&binary).unwrap();
  let out=std::process::Command::new(binary).arg("--version").output().unwrap();assert!(out.status.success());assert!(String::from_utf8_lossy(&out.stdout).contains(VERSION));
 }

}
