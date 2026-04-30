"""TaskScheduler COM API 동작 확인 (subprocess spawn 0)."""
import win32com.client

scheduler = win32com.client.Dispatch("Schedule.Service")
scheduler.Connect()
root = scheduler.GetFolder("\\")
try:
    task = root.GetTask("AgenticOS_Orchestrator")
    print("Task name:", task.Name)
    print("Task state:", task.State)  # 1=disabled 2=queued 3=ready 4=running
    print("OK: COM API works without subprocess")
except Exception as e:
    print("Error:", e)
