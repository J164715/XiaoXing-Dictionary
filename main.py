# main.py
import tkinter as tk
import traceback
import sys
import os

if __name__ == "__main__":
    try:
        # 启动时确保生成 config.json（如果没有的话）
        from settings import load_config

        load_config()

        # 直接加载主界面
        from ui import DictionaryApp

        root = tk.Tk()
        app = DictionaryApp(root)
        root.mainloop()
    except Exception as e:
        # 如果启动失败，写入日志并弹窗提示
        error_msg = traceback.format_exc()
        with open("error_log.txt", "w", encoding="utf-8") as f:
            f.write(error_msg)

        try:
            import tkinter.messagebox as msgbox

            r = tk.Tk()
            r.withdraw()
            msgbox.showerror("严重错误", f"程序发生错误，详情见 error_log.txt\n\n{str(e)}")
        except:
            pass
        sys.exit(1)