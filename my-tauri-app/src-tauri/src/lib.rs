// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

use std::process::Command;
use tauri::{Manager, RunEvent};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![greet])
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    let resource_dir = app.path().resource_dir().unwrap_or_default();

    // Tratamos de encontrar el server.py.
    // Para producción con sidecar la ruta real será el resource_dir
    // Para desarrollo (cargo run) es usualmente la raiz del repo "../server.py"
    let dev_server_path = std::path::Path::new("../server.py");

    let server_path_to_run = if dev_server_path.exists() {
        dev_server_path.to_path_buf()
    } else {
        resource_dir.join("server.py")
    };

    let mut child = Command::new("python")
        .arg(&server_path_to_run)
        .spawn()
        .expect("failed to execute python server");

    app.run(move |_app_handle, event| match event {
        RunEvent::Exit => {
            let _ = child.kill();
        }
        _ => {}
    });
}
