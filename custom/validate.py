from jupyterhub_entrypoint.api import BaseValidator
from jupyterhub.services.auth import HubAuthenticated
import asyncssh
import os

# can be used to override BaseValidator by including the following in entrypoint_config.py:
# c.APIBaseHandler.validator = SSHValidator()


class SSHValidator(BaseValidator, HubAuthenticated):
    """Uses ssh to communicate to remote systems and ensure paths are valid"""

    async def validate(self, user, path, entrypoint_type, hosts):
        result = True

        for host in hosts:
            print(f'Validating {path} ({entrypoint_type}) ({user}@{host})')

            if entrypoint_type == 'conda':
                result = result and await self._validate_conda(user, path, host)
            elif entrypoint_type == 'script':
                result = result and self._validate_script(user, path, host)
            elif entrypoint_type == 'shifter':
                result = result and self._validate_shifter(user)
            else:
                return False, 'Error: invalid entrypoint type'
        
        return result

    async def _validate_script(self, user, path, host):
        try:
            response = await self._check_script(user, path, host)
            print(response)

            if (response.exit_status != 0):
                return False, f'Error ({host}): ' + str(response.stderr)

            response = response.stdout
            response = response.split(' ')[0]

            # check if owner has execute privileges
            # e.g. file should have permissions -rwxr--r--
            if response[3] != 'x':
                return False, f'Error ({host}): File is not executable'

            return True, 'Validation successful'
        except asyncssh.Error as exc:
            # occurs when file is not found
            if 'non-zero exit status 2' in str(exc): 
                print('Error: ' + str(exc))
                return False, f'Error ({host}): Invalid path, no such file or directory'

            # otherwise the error most likely is because of invalid ssh cert
            print('SSHError: ' + str(exc))
            return False, f'SSHError ({host}): ' + str(exc)
        except OSError as exc:
            print('OSError: ' + str(exc))
            return False, f'OSError ({host}): ' + str(exc)
        except Exception as exc:
            print('Error: ' + str(exc))
            return False, f'Error ({host}): ' + str(exc)

    async def _check_script(self, user, path, host):
        async with asyncssh.connect(host, client_keys=[f'/certs/{user}.key'], username=user) as conn:
            response = await conn.run(f'ls -la {path}', check=True)
            return response

    async def _validate_conda(self, user, path, host):
        try:
            response = await self._check_conda_env(user, path, host)
            print('Response:')
            print(response)

            if (response.exit_status != 0):
                return False, f'Error ({host}): ' + str(response.stderr)

            response = response.stdout
            response = response.split(' ')[0]

            # check if owner has execute privileges
            # e.g. file should have permissions -rwxr--r--
            if response[3] != 'x':
                return False, f'Error ({host}): {os.path.join(path, "bin", "jupyter-labhub")} is not executable'
            return True, 'Validation successful'
        except (asyncssh.Error) as exc:
            print('SSHError: SSH connection failed: ' + str(exc))
            return False, f'SSHError ({host}): SSH connection failed: ' + str(exc)
        except (OSError) as exc:
            print('OSError: ' + str(exc))
            return False, f'OSError ({host}): ' + str(exc)
        except Exception as exc:
            print('Error: ' + str(exc))
            return False, f'Error ({host}): ' + str(exc)

    async def _check_conda_env(self, user, path, host):
        async with asyncssh.connect(host, client_keys=[f'/certs/{user}.key'], username=user) as conn:
            response = await conn.run(f'ls -la {os.path.join(path, "bin", "jupyter-labhub")}')
            return response

    def _clean_response(self, response):
        response = response.split('\n')[2:]
        response = list(map(lambda x: x.split(' '), response))

        res = []
        for arr in response:
            tmp = list(filter(lambda x: x != '' and x != '*', arr))
            if len(tmp) > 0:
                res.append(tmp[1])
        return res

    async def _validate_shifter(self, user):
        return True, 'Shifter images assumed to be valid'