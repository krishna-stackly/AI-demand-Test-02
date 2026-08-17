# EC2 deployment notes

This project is prepared for a single EC2 host running Docker Compose.

## Recommended host layout

- Root volume: 50 GB
- `/var`: 10 GB, containing Docker's data root (`/var/lib/docker`)
- Remaining root space: OS, project checkout, logs, and other host files

The 10 GB Docker filesystem is workable for this stack after the dependency/image
optimizations in this release, but it is still a tight production limit because
Docker stores images, writable layers, volumes, and build cache under its data
root. Monitor it with:

```bash
df -h /var
docker system df
```

## First deployment

From the project root:

```bash
cp .env.example .env
vi .env
```

Set production MySQL credentials and generate a strong `JWT_SECRET_KEY`.

Then build the services. Building the backend API and worker separately reduces
peak disk pressure on a 10 GB Docker filesystem:

```bash
docker compose build backend

docker compose build celery-worker

docker compose build nginx
```

Start the stack:

```bash
docker compose up -d
```

Check status:

```bash
docker compose ps
docker compose logs --tail=100 backend
docker compose logs --tail=100 celery-worker
docker compose logs --tail=100 nginx
```

The public application is served on port 80.

## Disk management

After a successful build, inspect usage:

```bash
docker system df
df -h /var
```

If build cache is consuming too much of the 10 GB Docker filesystem, remove
unused BuildKit cache:

```bash
docker builder prune -f
```

Do **not** run `docker volume prune` on a production host unless you have
confirmed that no MySQL/application data is stored in an unused volume.

## Important production behavior

The FastAPI API image does not contain the heavy ML training stack. Forecast
training/execution is delegated to the Celery worker through Redis.

The Celery worker image contains:

- XGBoost
- Prophet + CmdStan
- Statsmodels
- scikit-learn
- CPU-only PyTorch

Redis and MySQL must therefore remain healthy for normal asynchronous job
execution.
