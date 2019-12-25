#!/bin/bash
if [ -f edt.db ]; then
  if [ ! -d alembic ]; then
    alembic init alembic
    sed -i '/sqlalchemy.url/s/= .*/= sqlite:\/\/\/edt.db/' alembic.ini
    sed -i "/target_metadata = None/s/target_metadata.*/import os, sys\nsys.path.append(os.getcwd())\nfrom base import Base\ntarget_metadata = Base.metadata/" alembic/env.py
  fi

  alembic revision --autogenerate -m "Auto upgrade"
  alembic upgrade head
else
  echo "No database !"
fi
