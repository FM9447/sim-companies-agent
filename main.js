const { app, BrowserWindow, Menu, Tray, shell, nativeImage, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

// Ensure single instance lock
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
  process.exit(0);
}

let mainWindow = null;
let tray = null;

// Paths
const iconPath = path.join(__dirname, 'icon.png');
const stateFilePath = path.join(app.getPath('userData'), 'window-state.json');

// Window state load/save helpers
function loadWindowState() {
  try {
    if (fs.existsSync(stateFilePath)) {
      const data = fs.readFileSync(stateFilePath, 'utf8');
      return JSON.parse(data);
    }
  } catch (err) {
    console.error('Failed to load window state:', err);
  }
  return { width: 1400, height: 900, isMaximized: false };
}

function saveWindowState() {
  if (!mainWindow) return;
  try {
    const isMaximized = mainWindow.isMaximized();
    if (!isMaximized) {
      const bounds = mainWindow.getBounds();
      fs.writeFileSync(stateFilePath, JSON.stringify({ ...bounds, isMaximized: false }));
    } else {
      fs.writeFileSync(stateFilePath, JSON.stringify({ isMaximized: true }));
    }
  } catch (err) {
    console.error('Failed to save window state:', err);
  }
}

function createWindow() {
  const windowState = loadWindowState();

  mainWindow = new BrowserWindow({
    title: 'Sim Companies',
    x: windowState.x,
    y: windowState.y,
    width: windowState.width || 1400,
    height: windowState.height || 900,
    minWidth: 960,
    minHeight: 600,
    backgroundColor: '#1b2028',
    icon: iconPath,
    autoHideMenuBar: false,
    webPreferences: {
      partition: 'persist:simcompanies',
      nodeIntegration: false,
      contextIsolation: true,
      spellcheck: true
    }
  });

  if (windowState.isMaximized) {
    mainWindow.maximize();
  }

  // Optimize window title
  mainWindow.webContents.on('page-title-updated', (event, title) => {
    if (!title.toLowerCase().includes('sim companies')) {
      mainWindow.setTitle(`${title} - Sim Companies`);
      event.preventDefault();
    }
  });

  // Intercept external links and open them in the system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    try {
      const parsed = new URL(url);
      if (parsed.hostname.endsWith('simcompanies.com') && !url.includes('/auth/stripe/') && !url.includes('/auth/paypal/')) {
        return { action: 'allow' };
      }
    } catch (_) {}
    
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    try {
      const parsed = new URL(url);
      if (!parsed.hostname.endsWith('simcompanies.com')) {
        event.preventDefault();
        shell.openExternal(url);
      }
    } catch (_) {}
  });

  // Save state on close / resize
  mainWindow.on('close', () => {
    saveWindowState();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Load Sim Companies
  mainWindow.loadURL('https://www.simcompanies.com/');
}

function buildMenu() {
  const template = [
    {
      label: '&Game',
      submenu: [
        {
          label: 'Realm 1: Magnates',
          accelerator: 'CmdOrCtrl+1',
          click: () => mainWindow && mainWindow.loadURL('https://www.simcompanies.com/')
        },
        {
          label: 'Realm 2: Entrepreneurs',
          accelerator: 'CmdOrCtrl+2',
          click: () => mainWindow && mainWindow.loadURL('https://www.simcompanies.com/realm/2/')
        },
        { type: 'separator' },
        {
          label: 'Reload Page',
          accelerator: 'CmdOrCtrl+R',
          click: () => mainWindow && mainWindow.reload()
        },
        {
          label: 'Hard Reload (Clear Cache)',
          accelerator: 'CmdOrCtrl+Shift+R',
          click: () => mainWindow && mainWindow.webContents.reloadIgnoringCache()
        },
        { type: 'separator' },
        {
          label: 'Quit Sim Companies',
          accelerator: 'CmdOrCtrl+Q',
          click: () => app.quit()
        }
      ]
    },
    {
      label: '&View',
      submenu: [
        {
          label: 'Toggle Full Screen',
          accelerator: 'F11',
          click: () => mainWindow && mainWindow.setFullScreen(!mainWindow.isFullScreen())
        },
        { type: 'separator' },
        {
          label: 'Zoom In',
          accelerator: 'CmdOrCtrl+=',
          click: () => {
            if (mainWindow) {
              const current = mainWindow.webContents.getZoomLevel();
              mainWindow.webContents.setZoomLevel(current + 0.5);
            }
          }
        },
        {
          label: 'Zoom Out',
          accelerator: 'CmdOrCtrl+-',
          click: () => {
            if (mainWindow) {
              const current = mainWindow.webContents.getZoomLevel();
              mainWindow.webContents.setZoomLevel(current - 0.5);
            }
          }
        },
        {
          label: 'Reset Zoom',
          accelerator: 'CmdOrCtrl+0',
          click: () => mainWindow && mainWindow.webContents.setZoomLevel(0)
        },
        { type: 'separator' },
        {
          label: 'Toggle Developer Tools',
          accelerator: 'CmdOrCtrl+Shift+I',
          click: () => mainWindow && mainWindow.webContents.toggleDevTools()
        }
      ]
    },
    {
      label: '&Community & Guides',
      submenu: [
        {
          label: 'Official Guides & FAQ',
          click: () => shell.openExternal('https://www.simcompanies.com/pages/faq/')
        },
        {
          label: 'Sim Companies Wiki',
          click: () => shell.openExternal('https://simcompanies.fandom.com/wiki/Simcompanies_Wiki')
        },
        {
          label: 'Community Forum',
          click: () => shell.openExternal('https://www.simcompanies.com/forum/')
        },
        {
          label: 'Sim Companies Discord',
          click: () => shell.openExternal('https://discord.gg/simcompanies')
        },
        { type: 'separator' },
        {
          label: 'About Sim Companies Desktop',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About Sim Companies Desktop',
              message: 'Sim Companies Desktop for Linux',
              detail: 'Version 1.0.0\nA dedicated desktop client for Sim Companies with persistent profiles and native desktop integration.\n\nWebsite: https://www.simcompanies.com'
            });
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

function createTray() {
  if (!fs.existsSync(iconPath)) return;

  const trayIcon = nativeImage.createFromPath(iconPath).resize({ width: 24, height: 24 });
  tray = new Tray(trayIcon);
  tray.setToolTip('Sim Companies');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open Sim Companies',
      click: () => {
        if (mainWindow) {
          if (mainWindow.isMinimized()) mainWindow.restore();
          mainWindow.show();
          mainWindow.focus();
        } else {
          createWindow();
        }
      }
    },
    {
      label: 'Realm 1: Magnates',
      click: () => {
        if (mainWindow) mainWindow.loadURL('https://www.simcompanies.com/');
      }
    },
    {
      label: 'Realm 2: Entrepreneurs',
      click: () => {
        if (mainWindow) mainWindow.loadURL('https://www.simcompanies.com/realm/2/');
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => app.quit()
    }
  ]);

  tray.setContextMenu(contextMenu);
  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.focus();
      } else {
        mainWindow.show();
      }
    }
  });
}

// App lifecycle
app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
  }
});

app.whenReady().then(() => {
  buildMenu();
  createWindow();
  try {
    createTray();
  } catch (err) {
    console.warn('Tray initialization skipped:', err.message);
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
