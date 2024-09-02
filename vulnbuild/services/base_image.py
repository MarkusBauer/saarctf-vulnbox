import subprocess

from vulnbuild.services.services import Service


def docker_image_exists(image_name: str) -> bool:
    output = subprocess.check_output(['docker', 'images', '-q', image_name])
    return len(output) >= 12


class DefaultCiBaseImage:
    def __init__(self, image_name: str = 'saarsec/saarctf-ci-base') -> None:
        self.image_name = image_name

    def exists(self) -> bool:
        return docker_image_exists(self.image_name)

    def build(self, service: Service) -> None:
        path = service.folder / 'gamelib' / 'ci' / 'docker-saarctf-ci-base'
        print(f'[-] Image {self.image_name} is not present, building ...')
        subprocess.check_call([path / 'docker-build.sh'], cwd=path)
        print(f'[*] Image {self.image_name} has been created.')
