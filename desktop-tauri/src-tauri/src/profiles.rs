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
            "SELECT id,name,password FROM profiles WHERE name=?1",
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
