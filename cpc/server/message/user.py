from cpc.server.state.user_handler import UserLevel, UserHandler, UserError
import cpc.server.message
from cpc.util.version import __version__
from server_command import ServerCommand

class SCLogin(ServerCommand):
    """Logs in a user"""
    def __init__(self):
        ServerCommand.__init__(self, "login")

    def run(self, serverState, request, response):
        user=request.getParam('user')
        password=request.getParam('password')
        userhandler = UserHandler()
        user_obj = userhandler.validateUser(user,password)
        if user_obj is None:
            raise cpc.util.CpcError("Invalid user/pass")
        request.session.reset()
        request.session['default_project_name'] = None
        request.session['user'] = user_obj

        response.add('Logged in as %s'%user)

class SCAddUser(ServerCommand):
    """Adds a user to the system"""
    def __init__(self):
        ServerCommand.__init__(self, "add-user")

    def run(self, serverState, request, response):
        user=request.getParam('user')
        password=request.getParam('password')
        userhandler = UserHandler()
        try:
            userhandler.addUser(user,password, UserLevel.REGULAR_USER)
        except UserError as e:
            raise cpc.util.CpcError("Error adding user: %s"%str(e))
        response.add('Created user %s'%user)

class SCDeleteUser(ServerCommand):
    """Deletes a user from the system"""
    def __init__(self):
        ServerCommand.__init__(self, "delete-user")

    def run(self, serverState, request, response):
        target_str=request.getParam('user')
        userhandler = UserHandler()
        target_user_obj=userhandler.getUserFromString(target_str)
        if target_user_obj is None:
            raise ServerCommandError("User %s doesn't exist"%target_str)
        userhandler.deleteUser(target_user_obj)
        response.add('Deleted user %s'%target_str)

class SCPromoteUser(ServerCommand):
    """Promotes a user to the next level"""
    def __init__(self):
        ServerCommand.__init__(self, "promote-user")

    def run(self, serverState, request, response):
        user=request.getParam('user')
        userhandler = UserHandler()
        try:
            user_obj = userhandler.getUserFromString(user)
            user_obj.promote()
            response.add('Promoted user %s to level %s'%(
                user, user_obj.getUserlevelAsString()))
        except UserError as e:
            raise cpc.util.CpcError("Error promoting user: %s"%str(e))

class SCDemoteUser(ServerCommand):
    """Demotes a user to the previous level"""
    def __init__(self):
        ServerCommand.__init__(self, "demote-user")

    def run(self, serverState, request, response):
        user=request.getParam('user')
        userhandler = UserHandler()
        try:
            user_obj = userhandler.getUserFromString(user)
            user_obj.demote()
            response.add('Demoted user %s to level %s'%(
                user, user_obj.getUserlevelAsString()))
        except UserError as e:
            raise cpc.util.CpcError("Error demoting user: %s"%str(e))