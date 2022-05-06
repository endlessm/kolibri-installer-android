from kolibri_android.globals import initialize

initialize()

def main():
    from kolibri_android.frontend.application import Application
    frontend_application = Application()
    frontend_application.run()

if __name__ == "__main__":
    main()
