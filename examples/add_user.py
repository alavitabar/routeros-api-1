import sys
import socket
import routeros



# print('Number of arguments:', len(sys.argv), 'arguments.')
# print ('Argument List:', str(sys.argv))

dst = sys.argv[1]
usern = sys.argv[2]
passw = sys.argv[3]
port = 8728

api = routeros.Api(dst, port, usessl=False, sslverify=False)
if api is None:
    print("could not open socket!")
    raise SystemExit


if not api.login(usern, passw):
    print("login faild!")
    raise SystemExit


user_params = {'name': sys.argv[4], 'group': sys.argv[6], 'password': sys.argv[5]}
user_add = api.add('/user', user_params)
print(user_add)
