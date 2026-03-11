FROM node:22-bookworm-slim

# Install Chrome Headless Shell system dependencies (Debian packages)
RUN apt-get update && apt-get install -y \
  libnss3 \
  libdbus-1-3 \
  libatk1.0-0 \
  libgbm-dev \
  libasound2 \
  libxrandr2 \
  libxkbcommon-dev \
  libxfixes3 \
  libxcomposite1 \
  libxdamage1 \
  libatk-bridge2.0-0 \
  libpango-1.0-0 \
  libcairo2 \
  libcups2 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# Install Chrome Headless Shell for Remotion rendering
RUN npx remotion browser ensure

COPY . .

# Create output directory for rendered videos
RUN mkdir -p /tmp/renders

EXPOSE 3000
CMD ["npx", "tsx", "server/index.ts"]
