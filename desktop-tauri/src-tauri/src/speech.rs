//! Optional LocalSpeech SDK and Russian recognition model, pinned by file checksums.
use serde::{Deserialize,Serialize};
use sha2::{Digest,Sha256};
use std::{fs,io::{Read,Write},path::{Path,PathBuf},sync::atomic::{AtomicBool,Ordering},time::Duration};
use tauri::{Manager,Emitter,State};
static BUSY:AtomicBool=AtomicBool::new(false);
static CANCEL:AtomicBool=AtomicBool::new(false);
#[derive(Deserialize,Serialize,Clone)]struct File{path:String,bytes:u64,sha256:String}
#[derive(Deserialize,Serialize,Clone)]struct Manifest{version:String,base:String,files:Vec<File>,#[serde(rename="apiVersion",default="api_version")]api_version:u32}
fn api_version()->u32{1}
fn manifest()->Manifest{serde_json::from_str(include_str!("../../../tutorial/static/pwa/local-speech-manifest.json")).unwrap()}
const HOST:&str="https://dimaystinov.github.io/pythontutor/static/";
fn valid_version(v:&str)->bool{v.len()<32&&v.split('.').count()==3&&v.split('.').all(|p|!p.is_empty()&&p.len()<8&&p.bytes().all(|c|c.is_ascii_digit()))}
fn root(app:&tauri::AppHandle)->Result<PathBuf,String>{Ok(app.path().app_data_dir().map_err(|e|e.to_string())?.join("speech"))}
fn directory(app:&tauri::AppHandle,v:&str)->Result<PathBuf,String>{if !valid_version(v){return Err("Неверная версия LocalSpeech.".into());}Ok(root(app)?.join(v))}
fn selected(app:&tauri::AppHandle)->String{root(app).ok().and_then(|p|fs::read_to_string(p.join("active")).ok()).filter(|v|valid_version(v)).unwrap_or("0.3.0".into())}
fn validate(m:&Manifest,v:&str)->Result<(),String>{
 if !valid_version(v)||m.version!=v||m.api_version!=1||m.base!=format!("{HOST}local-speech/{v}/")||m.files.is_empty()||m.files.len()>200{return Err("Версия SDK несовместима с PythonTutor.".into());}
 let mut paths=std::collections::HashSet::new();let mut total=0u64;
 for f in &m.files{if f.path=="installed"||f.path==".pythontutor-manifest.json"||f.path.starts_with('/')||f.path.split('/').any(|p|p.is_empty()||p=="."||p=="..")||!f.path.bytes().all(|c|c.is_ascii_alphanumeric()||b"/._-".contains(&c))||!paths.insert(&f.path)||f.bytes==0||f.bytes>300_000_000||f.sha256.len()!=64||!f.sha256.bytes().all(|c|c.is_ascii_hexdigit()){return Err("Неверный список файлов SDK.".into());}total=total.checked_add(f.bytes).ok_or("Слишком большой пакет")?;}
 if total>500_000_000||!paths.contains(&"local-speech.mjs".to_string()){return Err("Неполный или слишком большой пакет SDK.".into());}Ok(())
}
fn installed_manifest(app:&tauri::AppHandle,v:&str)->Option<Manifest>{let dir=directory(app,v).ok()?;if !dir.join("installed").exists(){return None;}let m=fs::read(dir.join(".pythontutor-manifest.json")).ok().and_then(|b|serde_json::from_slice(&b).ok()).or_else(||(v=="0.3.0").then(manifest))?;validate(&m,v).ok()?;Some(m)}
fn allowed(path:&str)->bool{manifest().files.iter().any(|f|f.path==path)}
pub fn resource(app:&tauri::AppHandle,path:&str)->Option<Vec<u8>>{let tail=path.strip_prefix("/pythontutor/static/local-speech/")?;let (v,relative)=tail.split_once('/')?;let m=installed_manifest(app,v)?;if !m.files.iter().any(|f|f.path==relative){return None;}fs::read(directory(app,v).ok()?.join(relative)).ok()}
#[tauri::command]pub fn speech_status(app:tauri::AppHandle)->Result<bool,String>{Ok(installed_manifest(&app,&selected(&app)).is_some())}
#[tauri::command]pub fn speech_active_version(app:tauri::AppHandle)->String{selected(&app)}
#[tauri::command]pub fn speech_installed_versions(app:tauri::AppHandle)->Result<Vec<String>,String>{let p=root(&app)?;let mut result=Vec::new();if p.exists(){for e in fs::read_dir(p).map_err(|e|e.to_string())?.flatten(){if let Some(v)=e.file_name().to_str(){if valid_version(v)&&installed_manifest(&app,v).is_some(){result.push(v.to_string());}}}}Ok(result)}
fn activate(app:&tauri::AppHandle,v:&str)->Result<(),String>{if installed_manifest(app,v).is_none(){return Err("Сначала установите эту версию SDK.".into());}let p=root(app)?;let mut tmp=tempfile::NamedTempFile::new_in(&p).map_err(|e|e.to_string())?;tmp.write_all(v.as_bytes()).map_err(|e|e.to_string())?;tmp.persist(p.join("active")).map_err(|e|e.to_string())?;Ok(())}
#[tauri::command]pub fn activate_speech(app:tauri::AppHandle,state:State<'_,crate::AppState>,profile:String,version:String)->Result<(),String>{drop(state.checked(&profile)?);if BUSY.load(Ordering::SeqCst){return Err("Дождитесь окончания загрузки.".into());}activate(&app,&version)}
fn load_manifest(v:&str)->Result<Manifest,String>{if v=="0.3.0"{return Ok(manifest());}if !valid_version(v){return Err("Неверная версия SDK.".into());}let c=reqwest::blocking::Client::builder().timeout(Duration::from_secs(30)).build().map_err(|e|e.to_string())?;let r=c.get(format!("{HOST}local-speech/{v}/pythontutor-manifest.json")).send().and_then(|r|r.error_for_status()).map_err(|_|"Не удалось получить пакет SDK.")?;let mut bytes=Vec::new();r.take(1_000_001).read_to_end(&mut bytes).map_err(|e|e.to_string())?;if bytes.len()>1_000_000{return Err("Слишком большой список файлов.".into());}let m=serde_json::from_slice(&bytes).map_err(|_|"Неверный список файлов SDK.")?;validate(&m,v)?;Ok(m)}
#[tauri::command]pub fn cancel_speech(){CANCEL.store(true,Ordering::SeqCst);}
fn install(app:tauri::AppHandle,v:String)->Result<(),String>{
 let dir=directory(&app,&v)?;if installed_manifest(&app,&v).is_some(){return activate(&app,&v);}
 let parent=dir.parent().unwrap();fs::create_dir_all(parent).map_err(|e|e.to_string())?;let temp=tempfile::tempdir_in(parent).map_err(|e|e.to_string())?;
 let m=load_manifest(&v)?;validate(&m,&v)?;let manifest_bytes=serde_json::to_vec(&m).map_err(|e|e.to_string())?;let total:u64=m.files.iter().map(|f|f.bytes).sum();let mut done=0u64;
 let client=reqwest::blocking::Client::builder().connect_timeout(Duration::from_secs(15)).timeout(Duration::from_secs(300)).build().map_err(|e|e.to_string())?;
 for f in m.files{
  if CANCEL.load(Ordering::SeqCst){return Err("Загрузка отменена.".into());}
  let path=temp.path().join(&f.path);fs::create_dir_all(path.parent().unwrap()).map_err(|e|e.to_string())?;
  let mut response=client.get(format!("{}{}",m.base,f.path)).send().and_then(|r|r.error_for_status()).map_err(|e|e.to_string())?;
  let mut file=fs::File::create(path).map_err(|e|e.to_string())?;let mut hash=Sha256::new();let mut size=0u64;let mut buffer=vec![0;256*1024];
  loop{if CANCEL.load(Ordering::SeqCst){return Err("Загрузка отменена.".into());}let n=response.read(&mut buffer).map_err(|e|e.to_string())?;if n==0{break;}size+=n as u64;if size>f.bytes{return Err("Неверный размер файла LocalSpeech.".into());}hash.update(&buffer[..n]);file.write_all(&buffer[..n]).map_err(|e|e.to_string())?;let _=app.emit("speech-progress",serde_json::json!({"percent":(done+size)*100/total,"loaded":done+size,"total":total,"phase":"Скачивание"}));}
  if size!=f.bytes||format!("{:x}",hash.finalize())!=f.sha256{return Err("Файл LocalSpeech не прошёл проверку. Повторите скачивание.".into());}done+=size;
 }
 fs::write(temp.path().join(".pythontutor-manifest.json"),manifest_bytes).map_err(|e|e.to_string())?;
 fs::write(temp.path().join("installed"),v.as_bytes()).map_err(|e|e.to_string())?;
 if dir.exists(){fs::remove_dir_all(&dir).map_err(|e|e.to_string())?;}fs::rename(temp.path(),dir).map_err(|e|e.to_string())?;activate(&app,&v)
}
#[tauri::command]pub async fn install_speech(app:tauri::AppHandle,state:State<'_,crate::AppState>,profile:String,version:Option<String>)->Result<(),String>{
 drop(state.checked(&profile)?);if BUSY.swap(true,Ordering::SeqCst){return Err("Дождитесь загрузки LocalSpeech.".into());}CANCEL.store(false,Ordering::SeqCst);
 let result=tauri::async_runtime::spawn_blocking(move||install(app,version.unwrap_or("0.3.0".into()))).await.map_err(|e|e.to_string()).and_then(|r|r);BUSY.store(false,Ordering::SeqCst);result
}
#[tauri::command]pub fn remove_speech(app:tauri::AppHandle,state:State<'_,crate::AppState>,profile:String)->Result<(),String>{
 drop(state.checked(&profile)?);if BUSY.swap(true,Ordering::SeqCst){return Err("Сначала завершите или отмените скачивание LocalSpeech.".into());}
 let result=root(&app).and_then(|p|{if p.exists(){fs::remove_dir_all(p).map_err(|e|e.to_string())?;}Ok(())});BUSY.store(false,Ordering::SeqCst);result
}
#[cfg(test)]mod tests{use super::*;#[test]fn only_manifest_paths_are_served(){assert!(allowed("local-speech.mjs"));assert!(!allowed("../../learners.sqlite3"));assert!(!allowed("models/../../learners.sqlite3"));for f in manifest().files{assert!(!f.path.contains(".."));assert!(!Path::new(&f.path).is_absolute());assert!(f.bytes>0);assert_eq!(f.sha256.len(),64);}}}

#[cfg(test)]mod version_tests{use super::*;
 #[test]fn manifests_cannot_change_host_or_escape_version_directory(){let mut m=manifest();assert!(validate(&m,"0.3.0").is_ok());m.base="https://other.test/".into();assert!(validate(&m,"0.3.0").is_err());m=manifest();m.files[0].path="../active".into();assert!(validate(&m,"0.3.0").is_err());assert!(!valid_version("../0.3.0"));}
 #[test]fn incompatible_api_and_duplicate_paths_are_rejected(){let mut m=manifest();m.api_version=2;assert!(validate(&m,"0.3.0").is_err());m=manifest();m.files.push(m.files[0].clone());assert!(validate(&m,"0.3.0").is_err());}
}
