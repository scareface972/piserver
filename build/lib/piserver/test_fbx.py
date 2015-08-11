from modules import freebox

fbx = freebox.FreeboxOSCtrl()
status = fbx.getRegistrationStatus()

while (not fbx.isRegistered()):
	status = fbx.registerApp()
	if 'pending' != status: break;

if 'granted' == status:
	print(fbx.getTvStatus())
