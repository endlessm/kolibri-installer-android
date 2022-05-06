from kolibri_android.globals import initialize

initialize()

def main():
    from kolibri_android.remoteshell.application import Application
    remoteshell_application = Application()
    remoteshell_application.run()

if __name__ == "__main__":
    main()
