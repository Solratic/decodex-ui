# Decodex-UI

## Description

Decodex-UI is a cutting-edge tool designed to interpret and analyze on-chain transactions using the power of GPT (Generative Pre-trained Transformer) models. By leveraging natural language processing and machine learning, Decodex-UI aims to provide a more intuitive and user-friendly interface for comprehending complex blockchain transactions. Whether you are a blockchain enthusiast, a financial analyst, or a data scientist, Decodex-UI simplifies the process of transaction analysis, making the blockchain more accessible and transparent for everyone.

## Features

- Transaction Analysis: Interpret blockchain transactions without the need for technical knowledge.
- GPT-Powered Insights: Gain deeper understanding of transaction motives, risk factors, and other hidden details.
- User-Friendly Interface: A clean, easy-to-use UI that simplifies complex data.

## Prerequisites

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

## Installation and Usage

Follow these steps to get the application up and running:

### Step 1: Clone the Repository

Clone the repository to your local machine.

```bash
git clone https://github.com/your-username/decodex-ui.git
```

### Step 2: Setup Environment Variables

Copy `.env.example` to a new file called `.env`.

```bash
cp .env.example .env
```

Fill in the necessary variables in the `.env` file.

### Step 3: Run Docker Compose

Navigate to the project directory and execute the following command:

```bash
docker compose up -d
```

This will pull the necessary Docker images and start the Decodex-UI application.

### Step 4: Open the Application

Open your web browser and go to [localhost:8000](http://localhost:8000) to start using Decodex-UI.

## Usage

The following sections describe how to use the application with its api endpoints. You may check the [api docs here](http://loclahost:8000/docs)

You should start the app by running `docker compose up -d` in the project directory.

- Get transaction details

  ```bash
  curl localhost:8000/tx/0xeacbfa8fc611203120c93d8248eabd1a60b11ba103e8c5bdd773f83271e97a51
  ```

- Simulate a transaction

  ```bash
  curl localhost:8000/simulate/?from_address=0x31539c7a1bA66c74cAb1D05C5A1832CB583aA64D&to_address=0x898e51FDFd3DA66912330eB95788Fc3c26d2913C
  ```

```

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

## License

Decodex-UI is released under the MIT License. See the LICENSE file for more details.
```
