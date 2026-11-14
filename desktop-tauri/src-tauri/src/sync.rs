use crate::{profiles,AppState};
use rusqlite::{params,OptionalExtension};
use sha2::{Digest,Sha256};
use serde_json::{Value,json};
use tauri::State;
use std::time::Duration;

fn hash(input:&[u8])->String{format!("{:x}",Sha256::digest(input))}
async fn request(body:Value)->Result<Value,String>{
 let ca=reqwest::Certificate::from_pem(include_bytes!("sync-ca.pem")).map_err(|_|"Сертификат синхронизации недоступен")?;
 let c=reqwest::Client::builder().tls_built_in_root_certs(false).add_root_certificate(ca).redirect(reqwest::redirect::Policy::none()).timeout(Duration::from_secs(12)).build().map_err(|_|"Ошибка HTTPS")?;
 let r=c.post("https://109.196.164.69:8443/progress").json(&body).send().await.map_err(|_|"OFFLINE")?;
 if r.status().as_u16()==403{return Err("Неверный пароль.".into())}
 if !r.status().is_success(){return Err(format!("Синхронизация: HTTP {}",r.status().as_u16()))}
 r.json().await.map_err(|_|"Некорректный ответ сервера".into())
}
fn err(e:rusqlite::Error)->String{e.to_string()}
#[tauri::command]
pub async fn enter_course(state:State<'_,AppState>,surname:String,given_name:String,school_class:u8,password:String,old_pin:Option<String>,legacy:Option<String>)->Result<profiles::Profile,String>{
 if password.chars().count()<8||password.len()>256{return Err("Пароль: от 8 символов, не более 256 байт.".into())}
 let (identity,_,_)=profiles::student_details(&surname,&given_name,school_class,"0000")?;
 let uid=hash(format!("PythonTutor:student:v1:{identity}").as_bytes());
 let mut secret=[0u8;32];argon2::Argon2::default().hash_password_into(password.as_bytes(),uid.as_bytes(),&mut secret).map_err(|_|"Ошибка подготовки ключа")?;
 let proof=hash(&secret);
 let _guard=state.sync_gate.lock().await;
 let existing={let s=state.store.lock().map_err(|_|"Ошибка профиля")?;
 s.db.query_row("SELECT p.id,p.password FROM profiles p JOIN student_identities i ON p.id=i.profile WHERE i.identity=?1",[&identity],|r|Ok((r.get::<_,String>(0)?,r.get::<_,String>(1)?))).optional().map_err(err)?};
 if let Some((_,h))=&existing{
  use argon2::{Argon2,PasswordHash,PasswordVerifier};
  let ph=PasswordHash::new(h).map_err(|_|"Повреждён профиль")?;
  if Argon2::default().verify_password(password.as_bytes(),&ph).is_err(){
   let pin=old_pin.as_deref().unwrap_or("");
   if pin.len()!=4||!pin.bytes().all(|b|b.is_ascii_digit())||Argon2::default().verify_password(pin.as_bytes(),&ph).is_err(){return Err("Неверный пароль. Для перехода со старого PIN нажмите «У меня был PIN».".into())}
  }
 }
 if let Some(id)=&legacy{drop(state.checked(id)?);}
 let remote=request(json!({"op":"login","id":uid,"proof":proof})).await;
 if let Err(e)=&remote { if e!="OFFLINE" { return Err(e.clone()) } }
 let mut s=state.store.lock().map_err(|_|"Ошибка профиля")?;
 let p=if let Some((id,_))=existing{
  if old_pin.is_some(){s.db.execute("UPDATE profiles SET password=? WHERE id=?",params![profiles::pin_hash(&password)?,id]).map_err(err)?;}
  profiles::Profile{id,name:format!("{} · {} класс",identity.split('|').take(2).collect::<Vec<_>>().join(" "),school_class)}
 }else if let Some(id)=legacy{
  s.expire();if s.profile.as_ref().map(|p|&p.id)!=Some(&id){return Err("Войдите ещё раз".into())}
  profiles::convert_student(&mut s.db,&id,&surname,&given_name,school_class,&password)?
 }else{profiles::create_student(&mut s.db,&surname,&given_name,school_class,&password)?};
 s.db.execute("INSERT OR IGNORE INTO sync_state(profile,epoch,reset) VALUES(?,?,0)",params![p.id,remote.as_ref().ok().and_then(|r|r["epoch"].as_i64()).unwrap_or(-1)]).map_err(err)?;
 s.profile=Some(p.clone());s.last_activity=Some(std::time::SystemTime::now());
 s.sync_auth=Some((p.id.clone(),uid,proof));Ok(p)
}
#[tauri::command]
pub async fn sync_progress(state:State<'_,AppState>,profile:String)->Result<(),String>{
 let _guard=state.sync_gate.lock().await;
 let (uid,proof,epoch,reset,items)={let s=state.checked(&profile)?;
 let (_,uid,proof)=s.sync_auth.as_ref().filter(|a|a.0==profile).ok_or("Войдите ещё раз")?;
 let (epoch,reset):(i64,i64)=s.db.query_row("SELECT epoch,reset FROM sync_state WHERE profile=?",[&profile],|r|Ok((r.get(0)?,r.get(1)?))).map_err(err)?;
 let items=profiles::list(&s.db,&profile)?; (uid.clone(),proof.clone(),epoch,reset,items)};
 // Claim an offline-created identity with the same proof before synchronizing.
 let login=request(json!({"op":"login","id":uid,"proof":proof})).await?;
 let upload_epoch=if epoch<0 {login["epoch"].as_i64().ok_or("Нет версии прогресса")?}else{epoch};
 let send:Vec<_>=items.iter().map(|x|json!({"kind":x["kind"],"slug":x["slug"],"time":x["time"],"solved":x["solved"],"code":x["code"],"acceptedCode":x["acceptedCode"]})).collect();
 let reply=request(json!({"op":"sync","id":uid,"proof":proof,"epoch":upload_epoch,"reset":epoch>=0 && reset!=0,"items":send})).await?;
 let new_epoch=reply["epoch"].as_i64().ok_or("Нет версии прогресса")?;let rows=reply["items"].as_array().ok_or("Нет данных прогресса")?;
 let mut s=state.checked(&profile)?;let tx=s.db.transaction().map_err(err)?;
 let current:i64=tx.query_row("SELECT reset FROM sync_state WHERE profile=?",[&profile],|r|r.get(0)).map_err(err)?;
 if current!=reset{return Ok(())}
 let local=profiles::list(&tx,&profile)?;
 for x in &items{if new_epoch!=upload_epoch&&local.contains(x){tx.execute("DELETE FROM solutions WHERE profile=? AND kind=? AND slug=?",params![profile,x["kind"].as_str(),x["slug"].as_str()]).map_err(err)?;}}
 for x in rows{let old=local.iter().find(|y|y["kind"]==x["kind"]&&y["slug"]==x["slug"]);if old.is_some_and(|v|!items.contains(v)){continue}
 let mut record=x.clone();record["result"]=json!({"status":if x["solved"]==true{"ok"}else{"wrong_answer"}});profiles::save(&tx,&profile,record)?;}
 tx.execute("UPDATE sync_state SET epoch=?,reset=0 WHERE profile=?",params![new_epoch,profile]).map_err(err)?;tx.commit().map_err(err)
}
