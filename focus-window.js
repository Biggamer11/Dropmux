for (const w of workspace.windowList()) { if (String(w.caption) === "Dropmux") { w.minimized = false; workspace.activeWindow = w; } }
