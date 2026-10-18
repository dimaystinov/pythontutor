//! Optional LocalSpeech SDK and Russian recognition model, pinned by file checksums.
use serde::Deserialize;
use sha2::{Digest,Sha256};
use std::{fs,io::{Read,Write},path::{Path,PathBuf},sync::atomic::{AtomicBool,Ordering},time::Duration};
use tauri::{Manager,Emitter,State};
static BUSY:AtomicBool=AtomicBool::new(false);
static CANCEL:AtomicBool=AtomicBool::new(false);
#[derive(Deserialize)]struct File{path:String,bytes:u64,sha256:String}
#[derive(Deserialize)]struct Manifest{base:String,files:Vec<File>}
fn manifest()->Manifest{serde_json::from_str(include_str!("../../../tutorial/static/pwa/local-speech-manifest.json")).unwrap()}
fn directory(app:&tauri::AppHandle)->Result<PathBuf,String>{Ok(app.path().app_data_dir().map_err(|e|e.to_string())?.join("speech/0.3.0"))}
fn allowed(path:&str)->bool{manifest().files.iter().any(|f|f.path==path)}
pub fn resource(app:&tauri::AppHandle,path:&str)->Option<Vec<u8>>{let relative=path.strip_prefix("/pythontutor/static/local-speech/0.3.0/")?;if !allowed(relative){return None;}let dir=directory(app).ok()?;if !dir.join("installed").exists(){return None;}fs::read(dir.join(relative)).ok()}
#[tauri::command]pub fn speech_status(app:tauri::AppHandle)->Result<bool,String>{Ok(directory(&app)?.join("installed").exists())}
#[tauri::command]pub fn cancel_speech(){CANCEL.store(true,Ordering::SeqCst);}
fn install(app:tauri::AppHandle)->Result<(),String>{
 let dir=directory(&app)?;if dir.join("installed").exists(){return Ok(());}
 let parent=dir.parent().unwrap();fs::create_dir_all(parent).map_err(|e|e.to_string())?;let temp=tempfile::tempdir_in(parent).map_err(|e|e.to_string())?;
 let m=manifest();let total:u64=m.files.iter().map(|f|f.bytes).sum();let mut done=0u64;
 let client=reqwest::blocking::Client::builder().connect_timeout(Duration::from_secs(15)).timeout(Duration::from_secs(300)).build().map_err(|e|e.to_string())?;
 for f in m.files{
  if CANCEL.load(Ordering::SeqCst){return Err("Загрузка отменена.".into());}
  let path=temp.path().join(&f.path);fs::create_dir_all(path.parent().unwrap()).map_err(|e|e.to_string())?;
  let mut response=client.get(format!("{}{}",m.base,f.path)).send().and_then(|r|r.error_for_status()).map_err(|e|e.to_string())?;
  let mut file=fs::File::create(path).map_err(|e|e.to_string())?;let mut hash=Sha256::new();let mut size=0u64;let mut buffer=vec![0;256*1024];
  loop{if CANCEL.load(Ordering::SeqCst){return Err("Загрузка отменена.".into());}let n=response.read(&mut buffer).map_err(|e|e.to_string())?;if n==0{break;}size+=n as u64;if size>f.bytes{return Err("Неверный размер файла LocalSpeech.".into());}hash.update(&buffer[..n]);file.write_all(&buffer[..n]).map_err(|e|e.to_string())?;let _=app.emit("speech-progress",serde_json::json!({"percent":(done+size)*100/total,"loaded":done+size,"total":total,"phase":"Скачивание"}));}
  if size!=f.bytes||format!("{:x}",hash.finalize())!=f.sha256{return Err("Файл LocalSpeech не прошёл проверку. Повторите скачивание.".into());}done+=size;
 }
 fs::write(temp.path().join("installed"),b"0.3.0").map_err(|e|e.to_string())?;
 if dir.exists(){fs::remove_dir_all(&dir).map_err(|e|e.to_string())?;}fs::rename(temp.path(),dir).map_err(|e|e.to_string())?;Ok(())
}
#[tauri::command]pub async fn install_speech(app:tauri::AppHandle,state:State<'_,crate::AppState>,profile:String)->Result<(),String>{
 drop(state.checked(&profile)?);if BUSY.swap(true,Ordering::SeqCst){return Err("Дождитесь загрузки LocalSpeech.".into());}CANCEL.store(false,Ordering::SeqCst);
 let result=tauri::async_runtime::spawn_blocking(move||install(app)).await.map_err(|e|e.to_string()).and_then(|r|r);BUSY.store(false,Ordering::SeqCst);result
}
#[tauri::command]pub fn remove_speech(app:tauri::AppHandle,state:State<'_,crate::AppState>,profile:String)->Result<(),String>{
 drop(state.checked(&profile)?);if BUSY.swap(true,Ordering::SeqCst){return Err("Сначала завершите или отмените скачивание LocalSpeech.".into());}
 let result=directory(&app).and_then(|p|{if p.exists(){fs::remove_dir_all(p).map_err(|e|e.to_string())?;}Ok(())});BUSY.store(false,Ordering::SeqCst);result
}
#[cfg(test)]mod tests{use super::*;#[test]fn only_manifest_paths_are_served(){assert!(allowed("local-speech.mjs"));assert!(!allowed("../../learners.sqlite3"));assert!(!allowed("models/../../learners.sqlite3"));for f in manifest().files{assert!(!f.path.contains(".."));assert!(!Path::new(&f.path).is_absolute());assert!(f.bytes>0);assert_eq!(f.sha256.len(),64);}}}
