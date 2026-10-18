//! Apply an already downloaded and hash-verified installer without opening a browser.
use std::path::Path;

pub fn apply(path:&Path)->Result<(),String>{
 #[cfg(windows)]{
  let exe=std::env::current_exe().map_err(|e|e.to_string())?;
  let folder=exe.parent().ok_or("Не найдена папка приложения")?;
  std::process::Command::new(path).args(["/P","/UPDATE","/R"]).arg(format!("/D={}",folder.display())).spawn().map_err(|e|format!("Не удалось запустить обновление: {e}"))?;
  Ok(())
 }
 #[cfg(target_os="macos")]{macos(path)}
 #[cfg(not(any(windows,target_os="macos")))]{let _=path;Err("Автообновление поддерживается на Windows и macOS.".into())}
}

#[cfg(target_os="macos")]
fn macos(path:&Path)->Result<(),String>{
 use std::{fs,process::{Command,Stdio}};
 let exe=std::env::current_exe().map_err(|e|e.to_string())?;
 let bundle=exe.ancestors().find(|p|p.extension().is_some_and(|e|e=="app")).ok_or("Запустите установленное приложение из папки «Программы».")?;
 let parent=bundle.parent().ok_or("Не найдена папка приложения")?;
 let stage=tempfile::Builder::new().prefix(".pythontutor-update-").tempdir_in(parent).map_err(|_|"Нет доступа для обновления в этой папке. Переместите приложение в доступную вам папку «Программы».")?;
 let mount=tempfile::tempdir().map_err(|e|e.to_string())?;
 let attached=Command::new("/usr/bin/hdiutil").args(["attach","-nobrowse","-readonly","-mountpoint"]).arg(mount.path()).arg(path).output().map_err(|e|e.to_string())?;
 if !attached.status.success(){return Err("Не удалось открыть пакет обновления. Повторите загрузку.".into());}
 let source=mount.path().join("PythonTutor.app");let next=stage.path().join("next.app");
 let prepared=(||{
  let id=Command::new("/usr/libexec/PlistBuddy").args(["-c","Print :CFBundleIdentifier"]).arg(source.join("Contents/Info.plist")).output().map_err(|e|e.to_string())?;
  if !id.status.success()||String::from_utf8_lossy(&id.stdout).trim()!="org.pythontutor.desktop"{return Err("Пакет не является приложением PythonTutor.".into());}
  let result=Command::new("/usr/bin/ditto").arg(&source).arg(&next).status().map_err(|e|e.to_string())?;
  if !result.success(){return Err("Не удалось подготовить обновление. Проверьте свободное место.".into());}
  Ok::<(),String>(())
 })();
 let _=Command::new("/usr/bin/hdiutil").arg("detach").arg(mount.path()).output();prepared?;
 let script=stage.path().join("install.sh");fs::write(&script,MAC_INSTALL).map_err(|e|e.to_string())?;
 let log=fs::File::create(stage.path().join("update.log")).map_err(|e|e.to_string())?;
 Command::new("/bin/sh").arg(&script).arg(std::process::id().to_string()).arg(bundle).arg(stage.path()).stdin(Stdio::null()).stdout(Stdio::from(log.try_clone().map_err(|e|e.to_string())?)).stderr(Stdio::from(log)).spawn().map_err(|e|e.to_string())?;
 let _=stage.keep();Ok(())
}

// Paths are positional arguments, never interpolated into shell source. Keep the previous app for recovery.
#[cfg(any(target_os="macos",test))]
const MAC_INSTALL:&str=r#"#!/bin/sh
set -eu
pid=$1
target=$2
stage=$3
count=0
while kill -0 "$pid" 2>/dev/null; do
 count=$((count + 1))
 [ "$count" -lt 120 ] || exit 1
 sleep 1
done
/bin/mv "$target" "$stage/previous.app"
if ! /bin/mv "$stage/next.app" "$target"; then
 /bin/mv "$stage/previous.app" "$target"
 exit 1
fi
if ! /usr/bin/open "$target"; then
 /bin/mv "$target" "$stage/failed.app"
 /bin/mv "$stage/previous.app" "$target"
 /usr/bin/open "$target"
 exit 1
fi
"#;

#[cfg(all(test,unix))]
mod tests {
 use super::*;
 use std::{fs,process::Command};
 fn scenario(next:bool,open_ok:bool){
  let root=tempfile::tempdir().unwrap();let target=root.path().join("Python Tutor.app");let stage=root.path().join("update folder");
  fs::create_dir(&target).unwrap();fs::write(target.join("version"),"old").unwrap();fs::create_dir(&stage).unwrap();
  if next{fs::create_dir(stage.join("next.app")).unwrap();fs::write(stage.join("next.app/version"),"new").unwrap();}
  let script=root.path().join("test.sh");fs::write(&script,MAC_INSTALL.replace("/usr/bin/open",if open_ok{"/usr/bin/true"}else{"/usr/bin/false"})).unwrap();
  let status=Command::new("/bin/sh").arg(script).arg("99999999").arg(&target).arg(&stage).status().unwrap();
  assert_eq!(status.success(),next&&open_ok);
  assert_eq!(fs::read_to_string(target.join("version")).unwrap(),if next&&open_ok{"new"}else{"old"});
  if next&&open_ok{assert_eq!(fs::read_to_string(stage.join("previous.app/version")).unwrap(),"old");}
 }
 #[test]fn replaces_bundle_with_spaces_and_keeps_backup(){scenario(true,true);}
 #[test]fn failed_replacement_restores_previous_bundle(){scenario(false,true);}
 #[test]fn failed_launch_restores_previous_bundle(){scenario(true,false);}
}
