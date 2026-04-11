import sys
log = open("Q:/Claudework/bridge base/logs/rpa_debug.txt", "w", buffering=1)
log.write("start\n"); log.flush()
sys.stdout = log
sys.stderr = log
print("importing craigslist_auto_rpa..."); log.flush()
import craigslist_auto_rpa
print("import done"); log.flush()
print(f"CL_EMAIL={craigslist_auto_rpa.CL_EMAIL}"); log.flush()
log.close()
