from ..globals import initialize

initialize()


def main():
    from .application import Application

    application = Application()
    application.run()


main()
