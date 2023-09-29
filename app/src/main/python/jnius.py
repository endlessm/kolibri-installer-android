# Chaquopy to pyjnius compatibility wrapper. Unfortunately, even 3rd
# party packages in the Kolibri stack (zeroconf) expect to use pyjnius
# when they think they're on Android. Fortunately, chaquopy's
# java.jclass has a nearly identical interface to jnius.autoclass.
import java

autoclass = java.jclass
