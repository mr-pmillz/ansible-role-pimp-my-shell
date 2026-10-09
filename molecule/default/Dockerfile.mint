FROM linuxmintd/mint22-amd64:latest

ENV DEBIAN_FRONTEND=noninteractive
# Keep this image minimal: zsh/git/tmux/vim/bat/fontconfig/etc. are
# deliberately NOT pre-installed so the role's own prerequisite
# installation (tasks/prereqs.yml) is exercised by molecule.
# The apt lists are kept so the gantsign.oh-my-zsh dependency can
# install zsh/git before the role's own apt update runs.
RUN apt-get update \
  && apt-get install -y -q apt-utils \
  && apt-get install -y -q ca-certificates curl python3 python3-apt sudo bash iproute2 tini gnome-terminal dbus-x11 xvfb \
  && apt-get autoremove -y \
  && apt-get autoclean -y

WORKDIR /app
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh
RUN rm -rf /app

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
