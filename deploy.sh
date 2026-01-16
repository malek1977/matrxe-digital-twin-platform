#!/usr/bin/env bash
set -e
BRANCH=${1:-feature/fullstack-mvp}
echo "Deploying branch: $BRANCH"
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH
cd frontend || true
npm ci
npm run build
sudo rm -rf /var/www/matrxe/* || true
sudo cp -r dist/* /var/www/matrxe/ || true
cd ..
sudo docker compose build
sudo docker compose up -d
sudo docker compose exec backend npx prisma migrate deploy || true
echo "Deployment finished."
