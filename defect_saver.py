from pywinauto import Application
from pywinauto.keyboard import send_keys
from pywinauto.findwindows import ElementNotFoundError


file_name = "defects_exported"

def connect_application():
    app = Application(backend="uia").connect(path="C:\\Program Files\\Micro-Epsilon\\3DInspect 3.0")
    return app

def connect_main_window(app: Application):
    window = app.window(title_re="3DInspect")
    return window

def restore_window(window):
    try:
        window.set_focus()
    except Exception:
        window.maximize()  

def minimize_window(window):
    window.minimize()

def open_defects_menu(window):
    file_menu = window.child_window(title="File", control_type="MenuItem")
    export_defects_button = file_menu.child_window(auto_id="MainWindow.actionExport_defects")
    

    # Open and interact
    try:
        file_menu.expand()
    except ElementNotFoundError:
        print("Please ensure that the 3D inspect window is open and not minimized....")
        input("Press Enter to continue once the window is open...") # Jivan can u make this appear in the UI?
    
    export_defects_button.click_input()

def handle_export_popup(app, file_name):
    # Connect to export defects popup
    export_menu = app.window(title="Export defects")

    export_menu.wait(wait_for='visible', timeout=5, retry_interval=0.05)
    try:
        export_menu.set_focus()
        send_keys('{ENTER}', pause=0.02)   # press Enter
        export_menu.wait_not(wait_for_not = 'visible', timeout=5, retry_interval=0.05)  # quick check
        print("Popup handled via Enter key!")
    except Exception:
        export_menu.child_window(title="OK", control_type="Button").click()
        print("Popup handled via OK button!")
    return export_menu

def save_defects_file(main_window, file_name):

    popup = main_window.window(title_re="Export defects")
    filename = file_name
    edited = False

    # using win32 backend
    try:
        from pywinauto import Desktop
        handle = getattr(getattr(popup, "element_info", None), "handle", None)
        if handle:
            win32_popup = Desktop(backend="win32").window(handle=handle)
            if win32_popup.exists(timeout=0.5):
                try:
                    edit = win32_popup.Edit.wrapper_object()
                    edit.set_edit_text(filename)
                    print("Filename set via win32 Edit control.")
                    edited = True
                except Exception:
                    pass
    except Exception:
        pass
    if not edited:
        # check for the common auto_id edit
        edit_ctrl = popup.child_window(auto_id="1001", control_type="Edit")
        if edit_ctrl.exists(timeout=0.5):
            edit = edit_ctrl.wrapper_object()
            edit.set_edit_text(filename)
            print("Filename set via auto_id 1001 Edit control.")
        edited = True
    
    if not edited:
        # Any Edit control (quick check)
        edit_any = popup.child_window(control_type="Edit")
        if edit_any.exists(timeout=0.5):
            edit = edit_any.wrapper_object()
            edit.set_edit_text(filename)
            print("Filename set via Edit control.")
            edited = True

    # Click the Save (or OK) button
    saved = False
    try:
        popup.set_focus()
        send_keys('%s', pause=0.05)  # Alt+S
        # wait for dialog to close
        popup.wait_not(wait_for_not = 'visible', timeout=5, retry_interval = 0.05)
        saved = True
    except Exception:
        try:
            title = "Save"
            btn = popup.child_window(title=title, control_type="Button")
            btn.wait(wait_for='enabled', timeout=5, retry_interval=0.05)
            btn.click_input()
            saved = True
        except Exception:
            pass
    
    if not saved:
        raise RuntimeError("Could not find a Save/OK button on the popup")

    print("Popup handled, saved as:", filename)
    popup.wait_not(wait_for_not = 'visible', timeout=10, retry_interval = 0.05)

def save_defect_file(filename: str):
    file_name = filename
    app = connect_application()
    main_window = connect_main_window(app)
    
    open_defects_menu(main_window)
    
    handle_export_popup(app, file_name)
    save_defects_file(main_window, file_name)
    
if __name__ == "__main__":
    save_defect_file("defects_exported")
