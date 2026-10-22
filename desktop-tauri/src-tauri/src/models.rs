//! Verified, persistent model installation. Never execute files from downloads.
use std::{fs::{self, File}, io::{Read, Write}, path::Path, sync::atomic::{AtomicBool, Ordering}, time::Duration};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use tauri::{Emitter, Manager};
static BUSY: AtomicBool = AtomicBool::new(false);
static CANCEL: AtomicBool = AtomicBool::new(false);
const SERVER: &str = "https://dimaystinov.duckdns.org/models/Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC/";
const HF: &str = "https://huggingface.co/mlc-ai/Qwen2.5-Coder-7B-Instruct-q4f16_1-MLC/resolve/56dea5411b44b2a45cf0ceb16ead4c1f30141f49/";
const ZIP_HASH: &str = "76bc666dc023b1f7f8e458537a7a27d05f9b445475a0acd31012d43d918028d3";
const ZIP_SIZE: u64 = 4296797134;
#[derive(Deserialize, Clone)]
struct Asset { path: String, size: u64, sha256: String, source: String, group: String }
#[derive(Deserialize)]
struct Manifest { files: Vec<Asset> }
fn assets() -> Vec<Asset> {
    serde_json::from_str::<Manifest>(include_str!("../../../scripts/offline/assets.lock.json")).unwrap().files.into_iter().filter(|a| a.group == "qwen7b").collect()
}
fn active() -> Result<(), String> { if CANCEL.load(Ordering::Relaxed) { Err("Загрузка остановлена. Проверенные файлы сохранены.".into()) } else { Ok(()) } }
fn progress(app: &tauri::AppHandle, text: impl Into<String>) { let _ = app.emit("model-progress", text.into()); }
fn valid(path: &Path, size: u64, hash: &str) -> Result<bool, String> {
    if fs::metadata(path).map(|m| m.len()).unwrap_or(0) != size { return Ok(false); }
    let mut f = File::open(path).map_err(|e| e.to_string())?;
    let mut digest = Sha256::new(); let mut buf = vec![0; 1024*1024];
    loop { active()?; let n = f.read(&mut buf).map_err(|e| e.to_string())?; if n == 0 {break;} digest.update(&buf[..n]); }
    Ok(format!("{:x}", digest.finalize()) == hash)
}
fn download(client: &reqwest::blocking::Client, url: &str, dest: &Path, size: u64, hash: &str, app: &tauri::AppHandle, label: &str) -> Result<(), String> {
    active()?;
    let part = dest.with_extension("part");
    let result = (|| {
        let mut response = client.get(url).send().and_then(|r| r.error_for_status()).map_err(|e| e.to_string())?;
        let mut out = File::create(&part).map_err(|e| e.to_string())?;
        let mut digest = Sha256::new(); let mut count = 0u64; let mut previous = 101;
        let mut buf = vec![0; 1024*1024];
        loop { active()?; let n = response.read(&mut buf).map_err(|e| e.to_string())?; if n == 0 {break;}
            count += n as u64; if count > size {return Err("Размер загрузки превышает ожидаемый.".into());}
            out.write_all(&buf[..n]).map_err(|e| e.to_string())?; digest.update(&buf[..n]);
            let percent=count*100/size; if percent!=previous {progress(app,format!("{label} · {percent}%"));previous=percent;}
        }
        if count != size || format!("{:x}",digest.finalize()) != hash {return Err("Контрольная сумма загрузки не совпала.".into());}
        out.sync_all().map_err(|e|e.to_string())?; drop(out);
        fs::rename(&part,dest).map_err(|e|e.to_string())
    })();
    if result.is_err(){let _=fs::remove_file(&part);} result
}
fn extract(archive: &Path, root: &Path, files: &[Asset]) -> Result<(), String> {
    let mut zip = zip::ZipArchive::new(File::open(archive).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    // Exact manifest names only; no arbitrary archive paths are ever extracted.
    for a in files { active()?; let dest=root.join(&a.path);
        if valid(&dest,a.size,&a.sha256)? {continue;}
        let mut entry=zip.by_name(&a.path).map_err(|e|e.to_string())?;
        if entry.size()!=a.size {return Err("Неверный размер файла в архиве.".into());}
        let part=dest.with_extension("part"); let mut out=File::create(&part).map_err(|e|e.to_string())?;
        let mut buf=vec![0;1024*1024]; loop {active()?;let n=entry.read(&mut buf).map_err(|e|e.to_string())?;if n==0 {break;}out.write_all(&buf[..n]).map_err(|e|e.to_string())?;}
        drop(out); if !valid(&part,a.size,&a.sha256)? {let _=fs::remove_file(part);return Err("Повреждён файл модели.".into());}
        fs::rename(part,dest).map_err(|e|e.to_string())?;
    } Ok(())
}
fn install(app: tauri::AppHandle) -> Result<String,String> {
    let root=app.path().app_data_dir().map_err(|e|e.to_string())?.join("models");
    fs::create_dir_all(root.join("qwen7b")).map_err(|e|e.to_string())?;
    let files=assets();progress(&app,"Проверяю сохранённую модель…");
    let mut missing=Vec::new();for a in &files {if !valid(&root.join(&a.path),a.size,&a.sha256)? {missing.push(a.clone());}}
    if !missing.is_empty() {
        let client=reqwest::blocking::Client::builder().connect_timeout(Duration::from_secs(15)).timeout(Duration::from_secs(1800)).build().map_err(|e|e.to_string())?;
        let archive=root.join("qwen.zip");
        progress(&app,"Скачиваю модель с Яндекс Диска…");
        let yandex=(|| {
            if !valid(&archive,ZIP_SIZE,ZIP_HASH)? {
                let data:serde_json::Value=client.get("https://cloud-api.yandex.net/v1/disk/public/resources/download").query(&[("public_key","https://disk.yandex.ru/d/OMU394wW8v-5KQ")]).timeout(Duration::from_secs(25)).send().and_then(|r|r.error_for_status()).map_err(|e|e.to_string())?.json().map_err(|e|e.to_string())?;
                let url=data["href"].as_str().ok_or("Яндекс Диск не вернул ссылку.")?;
                download(&client,url,&archive,ZIP_SIZE,ZIP_HASH,&app,"Яндекс Диск")?;
            }
            progress(&app,"Проверяю и распаковываю модель…");extract(&archive,&root,&files)
        })();
        active()?;
        if yandex.is_ok(){let _=fs::remove_file(&archive);}
        else {
            progress(&app,"Яндекс Диск недоступен. Загружаю оставшиеся файлы с резервных источников…");
            for (i,a) in files.iter().enumerate() {
                active()?;let dest=root.join(&a.path);if valid(&dest,a.size,&a.sha256)? {continue;}
                let name=a.path.strip_prefix("qwen7b/").ok_or("Неверный путь модели")?;
                let fallback=if name=="model.wasm" {a.source.clone()} else {format!("{HF}{name}")};
                let mut ok=false;
                for (label,url) in [("Сервер",format!("{SERVER}{name}")),("Hugging Face / MLC",fallback)] {
                    active()?;
                    if download(&client,&url,&dest,a.size,&a.sha256,&app,&format!("{label} · файл {}/{}",i+1,files.len())).is_ok(){ok=true;break;}
                }
                active()?;if !ok{return Err(format!("Не удалось скачать {name}. Повторите попытку: проверенные файлы уже сохранены."));}
            }
        }
    }
    active()?;
    fs::copy(root.join("qwen7b/ndarray-cache.json"),root.join("qwen7b/tensor-cache.json")).map_err(|e|e.to_string())?;
    // Only installer-owned temporary files; never touch the user's Downloads.
    let _=fs::remove_file(root.join("qwen.zip"));
    let _=fs::remove_file(root.join("qwen.part"));
    for a in &files {let _=fs::remove_file(root.join(&a.path).with_extension("part"));}
    progress(&app,"Файлы модели проверены и сохранены.");
    Ok(root.to_string_lossy().into_owned())
}
#[tauri::command]
pub fn model_status(app: tauri::AppHandle) -> Result<serde_json::Value,String> {
    let root=app.path().app_data_dir().map_err(|e|e.to_string())?.join("models");
    let files=assets();
    let bytes:u64=files.iter().map(|a|a.size).sum();
    let complete=files.iter().all(|a|fs::metadata(root.join(&a.path)).map(|m|m.is_file()&&m.len()==a.size).unwrap_or(false));
    Ok(serde_json::json!({"installed":complete,"bytes":bytes}))
}
#[tauri::command]
pub async fn prepare_model(app: tauri::AppHandle, state: tauri::State<'_,crate::AppState>, profile:String) -> Result<String,String> {
    {drop(state.checked(&profile)?);}
    if BUSY.swap(true,Ordering::SeqCst){return Err("Дождитесь текущей загрузки модели.".into());}
    CANCEL.store(false,Ordering::SeqCst);
    let result=tauri::async_runtime::spawn_blocking(move||install(app)).await.map_err(|e|e.to_string()).and_then(|r|r);
    BUSY.store(false,Ordering::SeqCst);result
}
fn remove_downloads(root:&Path)->Result<(),String>{
    // This directory contains only the downloaded Qwen component, not course/profile data.
    let qwen=root.join("qwen7b");
    if qwen.exists(){fs::remove_dir_all(qwen).map_err(|e|e.to_string())?;}
    for name in ["qwen.zip","qwen.part"] {let p=root.join(name);if p.exists(){fs::remove_file(p).map_err(|e|e.to_string())?;}}
    Ok(())
}
#[tauri::command]
pub fn remove_model(app:tauri::AppHandle,state:tauri::State<'_,crate::AppState>,profile:String)->Result<(),String>{
    drop(state.checked(&profile)?);
    if BUSY.swap(true,Ordering::SeqCst){return Err("Дождитесь завершения или отмены загрузки модели.".into());}
    let result=app.path().app_data_dir().map_err(|e|e.to_string()).and_then(|p|remove_downloads(&p.join("models")));
    BUSY.store(false,Ordering::SeqCst);result
}
#[tauri::command]
pub fn cancel_model(){CANCEL.store(true,Ordering::SeqCst);}
#[cfg(test)]
mod tests {
 #[test]fn removal_preserves_other_data(){let d=tempfile::tempdir().unwrap();let root=d.path();fs::create_dir(root.join("qwen7b")).unwrap();fs::write(root.join("qwen7b/model.bin"),b"weights").unwrap();fs::write(root.join("qwen.part"),b"partial").unwrap();fs::write(root.join("profiles.db"),b"student").unwrap();fs::create_dir(root.join("speech")).unwrap();remove_downloads(root).unwrap();remove_downloads(root).unwrap();assert!(!root.join("qwen7b").exists());assert!(!root.join("qwen.part").exists());assert_eq!(fs::read(root.join("profiles.db")).unwrap(),b"student");assert!(root.join("speech").exists());}

 use super::*;
 #[test] fn rejects_corruption(){let dir=tempfile::tempdir().unwrap();let p=dir.path().join("x");fs::write(&p,b"abc").unwrap();assert!(valid(&p,3,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad").unwrap());assert!(!valid(&p,2,"bad").unwrap());assert!(!valid(&p,3,"bad").unwrap());}
 #[test] fn archive_extracts_only_verified_manifest_entries(){
  let dir=tempfile::tempdir().unwrap();let root=dir.path().join("models");fs::create_dir_all(root.join("qwen7b")).unwrap();
  let archive=dir.path().join("test.zip");let mut writer=zip::ZipWriter::new(File::create(&archive).unwrap());
  let options=zip::write::SimpleFileOptions::default().compression_method(zip::CompressionMethod::Stored);
  writer.start_file("qwen7b/test.bin",options).unwrap();writer.write_all(b"abc").unwrap();
  writer.start_file("../unexpected",options).unwrap();writer.write_all(b"ignore").unwrap();writer.finish().unwrap();
  let a=Asset{path:"qwen7b/test.bin".into(),size:3,sha256:"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad".into(),source:String::new(),group:"qwen7b".into()};
  extract(&archive,&root,&[a.clone()]).unwrap();assert_eq!(fs::read(root.join(&a.path)).unwrap(),b"abc");assert!(!dir.path().join("unexpected").exists());
  fs::remove_file(root.join(&a.path)).unwrap();let bad=Asset{sha256:"wrong".into(),..a};assert!(extract(&archive,&root,&[bad]).is_err());assert!(!root.join("qwen7b/test.bin").exists());assert!(!root.join("qwen7b/test.part").exists());
 }
 #[test] fn manifest_is_fixed_and_safe(){let files=assets();assert_eq!(files.len(),92);for a in files {assert!(a.path.starts_with("qwen7b/"));assert!(!a.path.contains(".."));assert_eq!(a.sha256.len(),64);assert!(a.size>0);}}
}
