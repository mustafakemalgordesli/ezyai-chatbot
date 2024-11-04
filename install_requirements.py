import subprocess

#Projedeki paketlerin sağlıklı bir şekilde yüklenmesini sağlar

with open('requirements.txt', 'r') as f:
    packages = f.readlines()

for package in packages:
    package = package.strip()
    if package: 
        print(f"Installing {package}...")
        try:
            subprocess.check_call([f"pip install {package}"], shell=True)
        except subprocess.CalledProcessError:
            print(f"Failed to install {package}, skipping...")