# 🏗️ Challenge: The Manual Data Pipeline Marathon

Welcome to today's lab. I will be 45 minutes late, so your mission is to build a functional 3-tier data stack (Database + Python Ingestor + Dashboard) using **pure Docker CLI commands**. 

If you finish early, you can start on Challenge 2.

**The Goal:** Connect PostgreSQL, Python, and Metabase without using a single configuration file.



## 🚫 The Rules
* **No Docker Compose allowed.** Everything must be done via the `docker` command line.
* Use a dedicated Docker Network (no default bridge).
* Data must persist if the database container is deleted or crashes.
* No AI Copilot allowed. 🆘 



## 📍 Step 1: The Infrastructure (Read carefully!)

Before our containers can talk or store anything permanently, we need to set up the foundation. 

### 💾 Mini-Lecture: Docker Volumes
By default, any data created inside a container is temporary. If the container is removed, the data dies with it. A **Volume** is like a virtual external hard drive that you plug into a container. It lives on your host machine, completely independent of the container's lifecycle. 
* 📖 **Docs:** [Docker Volumes Overview](https://docs.docker.com/storage/volumes/)
* **Your Task:** Create a volume named `pg-data`.

### 🌐 Mini-Lecture: Docker Networks
By default, containers are isolated and cannot easily talk to each other. Until now, you probably connected to containers using the IP address or by publishing ports to your host machine. If you put them on a custom **Bridge Network**, it acts like a private Wi-Fi router. The absolute best part? Docker provides automatic DNS resolution on custom networks. This means containers can talk to each other using their *container names* instead of IP addresses!
* 📖 **Docs:** [Docker Bridge Networks](https://docs.docker.com/network/network-tutorial-standalone/)
* **Your Task:** Create a custom bridge network named `data-tier`.



## 📍 Step 2: The Warehouse (PostgreSQL)

Launch a Postgres 15 container with the following requirements:
* **Name:** `warehouse`
* **Network:** Attach it to `data-tier`.
* **Volume:** Mount your `pg-data` volume to `/var/lib/postgresql/data`.
* **Environment:** Set the `POSTGRES_PASSWORD` environment variable to `secret123`.
* **Port:** Map the internal port `5432` to your host port `5432`.

> **Checkpoint:** Run `docker ps`. Is the database healthy? Can you connect to it from your laptop using a local SQL client (like DBeaver or `psql`) at `localhost:5432`?



## 📍 Step 3: The Python Script

Now, we need to send some data into that warehouse using a Python script. Let's do this "on the fly."

For this step, you already have a Python script in the repo called `ingest.py`. It will:
- create a table named `bootcamp_test` if it doesn't exist
- insert your name (from the `YOUR_NAME` environment variable)
It uses SQLAlchemy in the example container (for a nicer demo).

### The Big Question (Don't skip)
What *hostname* should the Python use to reach Postgres? It must be the container name: `warehouse` (NOT `localhost`).

1. Create a `Dockerfile` in the repo folder that builds a tiny image to run `ingest.py`.

2. Build your ingestor image:

3. Run it on the `data-tier` network, passing the name and Postgres credentials (using the .env file)




## 📍 Step 4: The Visualization (Metabase)

Let’s visualize the data. Launch a Metabase container:
* **Image:** `metabase/metabase:latest`
* **Name:** `viz-tool`
* **Network:** Attach it to `data-tier`.
* **Port:** Map it to `3000`.

**Task:** Open `localhost:3000` in your browser. Follow the setup wizard and connect it to your `warehouse` container using the credentials you set up in Step 2.



## 🧠 Discussion Questions (For when I arrive)
1. How many separate commands did you have to run to get this working?
2. If I force-delete the `warehouse` container and start a brand new one, will Metabase still show your `bootcamp_test` table? Why?
3. What happens if you try to start the Python script *before* the Postgres container is fully initialized?
4. If you wanted to hand this exact setup to a new hire, how many pages of instructions would you have to write?


**Good luck. See you in 45 minutes!**