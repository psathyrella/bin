#!/bin/bash

# NOTE can't run this script as a whole in one go, the idea is you copy/paste bits

# i don't think the pip stuff is right
sudo apt install build-essential libx11-dev gnutls-dev libxpm-dev libgif-dev libtinfo-dev git openssh-server i3 xfce4-terminal sshfs feh mosh gnome-screensaver python3-dev python3-pip python3-build python3-wheel python-is-python3 inkscape tmux units htop scrot scons texlive-full latexmk curl mafft tesseract-ocr iotop npm colordiff python3-termcolor
sudo snap install marktext #glow
# # ----------------------------------------------------------------------------------------
# # Install essential linear algebra libraries
# sudo apt update
# sudo apt install libblas-dev liblapack-dev

# # Install Boost development libraries
# sudo apt install libboost-all-dev

# # Optional: Install additional libraries for better performance
# sudo apt install libeigen3-dev libsuitesparse-dev libfftw3-dev
# # ----------------------------------------------------------------------------------------

ssh-keygen -t ed25519 -C "dkralph@gmail.com"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
# sign into firefox account
# sign into github, go to settings and add ssh public key above

# clone repos from github
git clone git@github.com:psathyrella/config
cp -rTv config ~  # this is a little risky, e.g. it does overwrite some changes in bashrc which maybe I should keep some of

xmodmap .xmodmap  # aaaaaah, yeah  NOTE now I think should use xmd command from Dropbox/bin

git clone git@github.com:psathyrella/emacs.d
mv emacs.d .emacs.d

# download emacs using firefox
./configure --with-x-toolkit=no --with-tiff=ifavailable --with-jpeg=ifavailable --with-png=ifavailable
make
make check  # slow af, and maybe pointless
sudo make install
make clean

# NOTE it may be better to start i3 first with the default config, then get this, since some things will probably be messed up (e.g. it'll hang if a package is missing)
git clone git@github.com:psathyrella/i3
mv i3 .config/
# then switch to desired branch, e.g. with:
git checkout --track origin/loraxis

# log out, log back in with i3

# install dropbox from their web site, follow instructions to link the new computer
# maybe this is best/works:
sudo dpkg -i Downloads/dropbox_2020.03.04_amd64.deb 
sudo apt-get -f install  # fixes missing deps

# change xfce4-terminal prefs by hand

# see Dropbox/work/commands.txt
gsettings set org.gnome.desktop.interface gtk-key-theme   "Emacs"
# then add to/create .config/gtk-3.0/settings.ini with lines:
    # Get firefox to use emacs keybindings
    [Settings]
    gtk-key-theme-name = Emacs
# then probably restart firefox

# ssh known hosts
# keys

# install magit (within emacs):
package-install # then enter 'magit'

# claude code
npx @anthropic-ai/claude-code

