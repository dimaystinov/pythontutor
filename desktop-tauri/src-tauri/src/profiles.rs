use argon2::{password_hash::SaltString, Argon2, PasswordHash, PasswordHasher, PasswordVerifier};
use rand_core::OsRng;
use rusqlite::{params, Connection, OptionalExtension};
use serde::Serialize;
use std::path::Path;
#[derive(Clone, Serialize)]
pub struct Profile {
    pub id: String,
    pub name: String,
}
pub fn open(path: &Path) -> Result<Connection, String> {
    let c = Connection::open(path).map_err(|e| e.to_string())?;
    c.execute_batch("PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY,name TEXT NOT NULL UNIQUE,password TEXT NOT NULL); CREATE TABLE IF NOT EXISTS solutions(profile TEXT NOT NULL,kind TEXT NOT NULL,slug TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(profile,kind,slug));").map_err(|e|e.to_string())?;
    c.execute_batch("CREATE TABLE IF NOT EXISTS student_identities(profile TEXT PRIMARY KEY,identity TEXT UNIQUE NOT NULL,surname TEXT NOT NULL,given_name TEXT NOT NULL,school_class INTEGER NOT NULL);").map_err(|e|e.to_string())?;
    Ok(c)
}
pub fn create(c: &Connection, name: &str, password: &str) -> Result<Profile, String> {
    let name = name.trim();
    if name.is_empty()
        || name.chars().count() > 60
        || password.chars().count() < 4
        || password.len() > 256
    {
        return Err("Укажите имя и пароль от 4 символов.".into());
    }
    let salt = SaltString::generate(&mut OsRng);
    let hash = Argon2::default()
        .hash_password(password.as_bytes(), &salt)
        .map_err(|e| e.to_string())?
        .to_string();
    let p = Profile {
        id: uuid::Uuid::new_v4().to_string(),
        name: name.into(),
    };
    c.execute(
        "INSERT INTO profiles VALUES(?1,?2,?3)",
        params![p.id, p.name, hash],
    )
    .map_err(|_| "Такое имя уже занято на этом компьютере.".to_string())?;
    Ok(p)
}
pub fn login(c: &Connection, name: &str, password: &str) -> Result<Profile, String> {
    let row: Option<(String, String, String)> = c
        .query_row(
            "SELECT id,name,password FROM profiles WHERE name=?1 AND NOT EXISTS (SELECT 1 FROM student_identities WHERE profile=profiles.id)",
            [name.trim()],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )
        .optional()
        .map_err(|e| e.to_string())?;
    let (id, name, hash) = row.ok_or("Неверное имя или пароль.")?;
    let parsed = PasswordHash::new(&hash).map_err(|_| "Повреждён профиль.")?;
    Argon2::default()
        .verify_password(password.as_bytes(), &parsed)
        .map_err(|_| "Неверное имя или пароль.")?;
    Ok(Profile { id, name })
}
fn student_details(surname: &str, given: &str, class: u8, pin: &str) -> Result<(String,String,String),String> {
    fn normalize(value: &str) -> Result<String,String> {
        let en = "qwertyuiop[]asdfghjkl;'zxcvbnm,.`";
        let ru: Vec<char> = "йцукенгшщзхъфывапролджэячсмитьбюё".chars().collect();
        let value: String = value.to_lowercase().chars().map(|c| en.chars().position(|x|x==c).map(|i|ru[i]).unwrap_or(c)).map(|c|if c=='ё' {'е'} else {c}).collect();
        let value = value.split_whitespace().collect::<Vec<_>>().join(" ");
        if value.is_empty() || value.chars().count()>40 || !value.chars().all(|c| ('а'..='я').contains(&c) || c=='-' || c==' ') {return Err("Укажите фамилию и имя русскими буквами.".into());}
        Ok(value)
    }
    if !(1..=11).contains(&class) {return Err("Класс — число от 1 до 11.".into());}
    if pin.len()!=4 || !pin.bytes().all(|b|b.is_ascii_digit()) {return Err("PIN-код должен содержать ровно 4 цифры.".into());}
    let surname=normalize(surname)?;let given=normalize(given)?;
    Ok((format!("{surname}|{given}|{class}"),surname,given))
}
fn pin_hash(pin:&str)->Result<String,String> {
    Argon2::default().hash_password(pin.as_bytes(),&SaltString::generate(&mut OsRng)).map(|h|h.to_string()).map_err(|e|e.to_string())
}
pub fn create_student(c:&mut Connection,surname:&str,given:&str,class:u8,pin:&str)->Result<Profile,String>{
    let (identity,surname,given)=student_details(surname,given,class,pin)?;
    let p=Profile{id:uuid::Uuid::new_v4().to_string(),name:format!("{surname} {given} · {class} класс")};
    let hash=pin_hash(pin)?;let tx=c.transaction().map_err(|e|e.to_string())?;
    tx.execute("INSERT INTO profiles VALUES(?1,?2,?3)",params![p.id,format!("$student:{}",p.id),hash]).map_err(|e|e.to_string())?;
    tx.execute("INSERT INTO student_identities VALUES(?1,?2,?3,?4,?5)",params![p.id,identity,surname,given,class]).map_err(|_|"Такой ученик уже зарегистрирован в этом классе.".to_string())?;
    tx.commit().map_err(|e|e.to_string())?;Ok(p)
}
pub fn login_student(c:&Connection,surname:&str,given:&str,class:u8,pin:&str)->Result<Profile,String>{
    let(identity,surname,given)=student_details(surname,given,class,pin)?;
    let row:Option<(String,String)>=c.query_row("SELECT p.id,p.password FROM profiles p JOIN student_identities s ON s.profile=p.id WHERE s.identity=?1",[identity],|r|Ok((r.get(0)?,r.get(1)?))).optional().map_err(|e|e.to_string())?;
    let(id,hash)=row.ok_or("Проверьте фамилию, имя, класс и PIN-код.")?;
    Argon2::default().verify_password(pin.as_bytes(),&PasswordHash::new(&hash).map_err(|_|"Повреждён профиль.")?).map_err(|_|"Проверьте фамилию, имя, класс и PIN-код.")?;
    Ok(Profile{id,name:format!("{surname} {given} · {class} класс")})
}
pub fn convert_student(c:&mut Connection,id:&str,surname:&str,given:&str,class:u8,pin:&str)->Result<Profile,String>{
    let(identity,surname,given)=student_details(surname,given,class,pin)?;let hash=pin_hash(pin)?;
    let tx=c.transaction().map_err(|e|e.to_string())?;
    tx.execute("INSERT INTO student_identities VALUES(?1,?2,?3,?4,?5)",params![id,identity,surname,given,class]).map_err(|_|"Такой ученик уже зарегистрирован.".to_string())?;
    if tx.execute("UPDATE profiles SET password=?1 WHERE id=?2",params![hash,id]).map_err(|e|e.to_string())?!=1{return Err("Профиль не найден.".into());}
    tx.commit().map_err(|e|e.to_string())?;
    Ok(Profile{id:id.into(),name:format!("{surname} {given} · {class} класс")})
}
pub fn list(c: &Connection, id: &str) -> Result<Vec<serde_json::Value>, String> {
    let mut q = c
        .prepare("SELECT data FROM solutions WHERE profile=?1")
        .map_err(|e| e.to_string())?;
    let rows = q
        .query_map([id], |r| r.get::<_, String>(0))
        .map_err(|e| e.to_string())?;
    rows.map(|r| serde_json::from_str(&r.map_err(|e| e.to_string())?).map_err(|e| e.to_string()))
        .collect()
}
pub fn save(c: &Connection, id: &str, mut data: serde_json::Value) -> Result<(), String> {
    let kind = data["kind"].as_str().ok_or("Нет типа задачи")?.to_owned();
    let slug = data["slug"].as_str().ok_or("Нет задачи")?.to_owned();
    if !["problem", "image"].contains(&kind.as_str())
        || slug.len() > 150
        || slug.is_empty()
        || !slug
            .chars()
            .all(|x| x.is_ascii_alphanumeric() || x == '_' || x == '-')
        || data.to_string().len() > 500_000
    {
        return Err("Неверные данные решения".into());
    }
    data["owner"] = id.into();
    data["key"] = format!("{id}:{kind}:{slug}").into();
    c.execute("INSERT INTO solutions VALUES(?1,?2,?3,?4) ON CONFLICT(profile,kind,slug) DO UPDATE SET data=excluded.data",params![id,kind,slug,data.to_string()]).map_err(|e|e.to_string())?;
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn offline_accounts_and_isolated_progress() {
        let d = tempfile::tempdir().unwrap();
        let path = d.path().join("profiles.db");
        let c = open(&path).unwrap();
        let a = create(&c, "Аня", "1234").unwrap();
        let b = create(&c, "Борис", "5678").unwrap();
        assert!(login(&c, "Аня", "5678").is_err());
        assert!(create(&c, "Аня", "1234").is_err());
        save(
            &c,
            &a.id,
            serde_json::json!({"kind":"problem","slug":"apples","solved":true}),
        )
        .unwrap();
        assert_eq!(list(&c, &a.id).unwrap().len(), 1);
        assert!(list(&c, &b.id).unwrap().is_empty());
        drop(c);
        let c = open(&path).unwrap();
        assert_eq!(login(&c, "Аня", "1234").unwrap().id, a.id);
        assert_eq!(list(&c, &a.id).unwrap().len(), 1);
    }
}

#[cfg(test)]
mod student_tests {
    use super::*;
    #[test]
    fn names_case_layout_class_and_pin() {
        let d=tempfile::tempdir().unwrap();let mut c=open(&d.path().join("p.db")).unwrap();
        let a=create_student(&mut c,"  ИВАНОВ ","Иван",5,"0123").unwrap();
        assert_eq!(login_student(&c,"bdfyjd","BDFY",5,"0123").unwrap().id,a.id);
        assert!(login_student(&c,"иванов","иван",6,"0123").is_err());
        assert!(login_student(&c,"иванов","иван",5,"123").is_err());
        assert!(login_student(&c,"иванов","иван",5,"9999").is_err());
        assert!(create_student(&mut c,"Иванов","Иван",5,"4567").is_err());
        assert!(create_student(&mut c,"Петров","Пётр",0,"1234").is_err());
        assert!(create_student(&mut c,"Петров","Пётр",6,"abcd").is_err());
        let b=create_student(&mut c,"Иванов","Иван",6,"0123").unwrap();assert_ne!(a.id,b.id);
    }
    #[test]
    fn legacy_conversion_preserves_id_and_solutions() {
        let d=tempfile::tempdir().unwrap();let path=d.path().join("p.db");let mut c=open(&path).unwrap();
        let old=create(&c,"old pupil","old password").unwrap();
        save(&c,&old.id,serde_json::json!({"kind":"problem","slug":"apples","solved":true})).unwrap();
        let p=convert_student(&mut c,&old.id,"Петров","Пётр",4,"0000").unwrap();assert_eq!(p.id,old.id);
        assert!(login(&c,"old pupil","old password").is_err());drop(c);
        let c=open(&path).unwrap();let p=login_student(&c,"петров","петр",4,"0000").unwrap();
        assert_eq!(p.id,old.id);assert_eq!(list(&c,&p.id).unwrap().len(),1);
    }
}
