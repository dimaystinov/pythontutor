//! Release discovery and verified installer download. URLs are never supplied by the webview.
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{fs, io::{Read, Write}, sync::atomic::{AtomicBool, Ordering}, time::Duration};
use tauri::{Emitter, Manager};
const API: &str = "https://api.github.com/repos/dimaystinov/pythontutor/releases?per_page=100";
const BASE: &str = "https://github.com/dimaystinov/pythontutor/releases/download/";
static BUSY: AtomicBool = AtomicBool::new(false);
static CANCEL: AtomicBool = AtomicBool::new(false);
#[derive(Deserialize)] struct Asset {#[serde(default)] id:u64, name:String, size:u64, browser_download_url:String}
#[derive(Deserialize)] struct Release {tag_name:String, draft:bool, prerelease:bool, assets:Vec<Asset>}
#[derive(Serialize)] pub struct Status {current:String, latest:Option<String>, available:bool}
fn version(s:&str)->Option<[u64;3]> {let p=s.split('.').map(str::parse::<u64>).collect::<Result<Vec<_>,_>>().ok()?;p.try_into().ok()}
fn filename(v:&str)->String {
 if cfg!(windows){format!("PythonTutor_{v}_x64-setup.exe")}else if cfg!(target_arch="aarch64"){format!("PythonTutor_{v}_aarch64.dmg")}else{format!("PythonTutor_{v}_x64.dmg")}
}
fn valid_asset(a:&Asset,tag:&str)->bool {a.size>0&&a.size<1_500_000_000&&a.browser_download_url==format!("{BASE}{tag}/{}",a.name)&&!a.name.contains('/')}
fn select(releases:Vec<Release>)->Option<Release>{releases.into_iter().filter(|r|!r.draft&&!r.prerelease).filter(|r|{
 let Some(v)=r.tag_name.strip_prefix("app-v").filter(|s|version(s).is_some()) else{return false;};
 [filename(v),"SHA256SUMS.txt".into()].iter().all(|name|r.assets.iter().any(|a|&a.name==name&&valid_asset(a,&r.tag_name)))
 }).max_by_key(|r|version(r.tag_name.trim_start_matches("app-v")))}
fn client()->Result<reqwest::blocking::Client,String>{reqwest::blocking::Client::builder().user_agent("PythonTutor-updater").connect_timeout(Duration::from_secs(15)).timeout(Duration::from_secs(1800)).build().map_err(|e|e.to_string())}
fn fetch_asset(c:&reqwest::blocking::Client,a:&Asset,timeout:Duration)->Result<reqwest::blocking::Response,String>{
 let first=c.get(&a.browser_download_url).timeout(timeout).send().and_then(|r|r.error_for_status());
 if let Ok(r)=first{return Ok(r);}
 if a.id>0 {
  let url=format!("https://api.github.com/repos/dimaystinov/pythontutor/releases/assets/{}",a.id);
  if let Ok(r)=c.get(url).header(reqwest::header::ACCEPT,"application/octet-stream").timeout(timeout).send().and_then(|r|r.error_for_status()){
   if !r.headers().get(reqwest::header::CONTENT_TYPE).and_then(|v|v.to_str().ok()).unwrap_or("").contains("json"){return Ok(r);}
  }
 }
 Err("Не удалось скачать обновление. Сервер загрузки недоступен. Текущая версия сохранена; повторите попытку позже.".into())
}
fn discover(c:&reqwest::blocking::Client)->Result<Release,String>{let releases=c.get(API).timeout(Duration::from_secs(30)).send().and_then(|r|r.error_for_status()).map_err(|_|"Не удалось проверить обновления. Проверьте подключение и повторите.")?.json().map_err(|_|"Неверный ответ сервера обновлений.")?;select(releases).ok_or("Готовый выпуск для этого компьютера не найден.".into())}
#[tauri::command]pub fn app_version()->String{env!("CARGO_PKG_VERSION").into()}
#[tauri::command]pub async fn check_update()->Result<Status,String>{tauri::async_runtime::spawn_blocking(||{
 let r=discover(&client()?)?;let latest=r.tag_name.trim_start_matches("app-v").to_string();let current=app_version();let available=version(&latest)>version(&current);Ok(Status{current,latest:Some(latest),available})
 }).await.map_err(|e|e.to_string())?}
fn checksum(text:&str,name:&str)->Result<String,String>{let mut lines=text.lines().filter_map(|l|{let mut p=l.split_whitespace();Some((p.next()?,p.next()?))}).filter(|(_,n)|*n==name);let (hash,_)=lines.next().ok_or("Нет контрольной суммы установщика.")?;if lines.next().is_some()||hash.len()!=64||!hash.bytes().all(|b|b.is_ascii_hexdigit()){return Err("Неверная контрольная сумма.".into());}Ok(hash.to_lowercase())}
fn emit(app:&tauri::AppHandle,bytes:u64,total:u64,text:&str){let _=app.emit("update-progress",serde_json::json!({"loaded":bytes,"total":total,"percent":if total>0{bytes*100/total}else{0},"text":text}));}
fn active()->Result<(),String>{if CANCEL.load(Ordering::SeqCst){Err("Скачивание отменено.".into())}else{Ok(())}}
fn install(app:tauri::AppHandle)->Result<String,String>{
 emit(&app,0,0,"Проверка выпуска…");let c=client()?;let r=discover(&c)?;active()?;let v=r.tag_name.trim_start_matches("app-v");if version(v)<=version(&app_version()){return Err("Уже установлена актуальная версия.".into());}
 let name=filename(v);let a=r.assets.iter().find(|a|a.name==name).unwrap();let sums=r.assets.iter().find(|a|a.name=="SHA256SUMS.txt").unwrap();
 let mut text=String::new();fetch_asset(&c,sums,Duration::from_secs(30))?.take(65536).read_to_string(&mut text).map_err(|e|e.to_string())?;let expected=checksum(&text,&name)?;
 let root=app.path().app_cache_dir().map_err(|e|e.to_string())?.join("updates");fs::create_dir_all(&root).map_err(|e|e.to_string())?;
 let mut temp=tempfile::NamedTempFile::new_in(&root).map_err(|e|e.to_string())?;let mut response=fetch_asset(&c,a,Duration::from_secs(1800))?;let mut hash=Sha256::new();let mut bytes=0;let mut buf=[0;256*1024];
 loop{active()?;let n=response.read(&mut buf).map_err(|e|e.to_string())?;if n==0{break;}bytes+=n as u64;if bytes>a.size{return Err("Размер установщика не совпал.".into());}temp.write_all(&buf[..n]).map_err(|e|e.to_string())?;hash.update(&buf[..n]);emit(&app,bytes,a.size,"Скачивание обновления");}
 emit(&app,bytes,a.size,"Проверка установщика…");if bytes!=a.size||format!("{:x}",hash.finalize())!=expected{return Err("Установщик не прошёл проверку. Повторите загрузку.".into());}active()?;temp.as_file().sync_all().map_err(|e|e.to_string())?;let path=root.join(name);temp.persist(&path).map_err(|e|e.to_string())?;
 emit(&app,bytes,a.size,"Установка обновления…");
 crate::update_install::apply(&path)?;
 let handle=app.clone();std::thread::spawn(move||{std::thread::sleep(Duration::from_secs(1));handle.exit(0);});
 Ok("Обновление подготовлено. PythonTutor перезапускается…".into())
}
#[tauri::command]pub async fn install_update(app:tauri::AppHandle,state:tauri::State<'_,crate::AppState>,profile:String)->Result<String,String>{drop(state.checked(&profile)?);if BUSY.swap(true,Ordering::SeqCst){return Err("Обновление уже скачивается.".into());}CANCEL.store(false,Ordering::SeqCst);let result=tauri::async_runtime::spawn_blocking(move||install(app)).await.map_err(|e|e.to_string()).and_then(|r|r);BUSY.store(false,Ordering::SeqCst);result}
#[tauri::command]pub fn finish_update(app:tauri::AppHandle){app.exit(0);}
#[tauri::command]pub fn cancel_update(){CANCEL.store(true,Ordering::SeqCst);}
#[cfg(test)]mod tests{use super::*;
 #[test]fn numeric_versions(){assert!(version("2.10.0")>version("2.9.9"));assert!(version("2.1.0-beta").is_none());assert!(version("2.1/0").is_none());}
 #[test]fn checksums_require_exact_name(){let h="a".repeat(64);assert_eq!(checksum(&format!("{h}  app.exe\n"),"app.exe").unwrap(),h);assert!(checksum(&format!("{h}  other.exe"),"app.exe").is_err());assert!(checksum("abc app.exe","app.exe").is_err());}
 #[test]fn reject_foreign_download(){let a=Asset{id:0,name:"x.exe".into(),size:1,browser_download_url:"https://evil.test/x.exe".into()};assert!(!valid_asset(&a,"app-v2.1.0"));}
 #[test]fn incomplete_release_is_not_available(){assert!(select(vec![Release{tag_name:"app-v9.0.0".into(),draft:false,prerelease:false,assets:vec![]}]).is_none());}
}
