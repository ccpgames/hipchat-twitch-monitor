


FROM python:2.7
MAINTAINER Ben Gruber <bgruber@ccpgames.com>

ADD /htm/requirements.txt
ADD /htm/monitor.py

RUN pip install -qU virtualenv \
  && virtualenv /venv \
  && /venv/bin/pip install -qUr /htm/requirements.txt

ENV TWITCH_HIPCHAT_TOKEN_V2 ""
ENV TWITCH_GAMES ""
ENV TWITCH_HIPCHAT_BASE_URI ""
ENV TWITCH_HIPCHAT_ROOM ""

WORKDIR /htm/
CMD /venv/bin/python /htm/monitor.py
