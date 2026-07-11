const path = require('path');
const fs = require('fs');
const solc = require('solc');
const { ethers } = require('ethers');
require('dotenv').config();

function updateEnv(deployedAddress) {
    const envPath = path.resolve(__dirname, '.env');
    let envContent = fs.readFileSync(envPath, 'utf8');
    
    const regex = /^PAYMENT_TOKEN_ADDRESS=.*$/m;
    if (regex.test(envContent)) {
        envContent = envContent.replace(regex, `PAYMENT_TOKEN_ADDRESS=${deployedAddress}`);
    } else {
        envContent += `\nPAYMENT_TOKEN_ADDRESS=${deployedAddress}`;
    }
    fs.writeFileSync(envPath, envContent, 'utf8');
    console.log(`\n[Env Config] Updated PAYMENT_TOKEN_ADDRESS in .env to ${deployedAddress}`);
}

async function main() {
    console.log("=== MockERC20 Token Deployment ===");
    
    const rpcUrl = process.env.X_LAYER_TESTNET_RPC_URL;
    const privateKey = process.env.ATTESTATION_WALLET_PRIVATE_KEY;
    const payerPrivateKey = process.env.TEST_PAYER_PRIVATE_KEY;

    if (!rpcUrl || !privateKey || !payerPrivateKey) {
        console.error("Missing required .env variables.");
        process.exit(1);
    }

    // 1. Compile contract
    const contractPath = path.resolve(__dirname, 'MockERC20.sol');
    const source = fs.readFileSync(contractPath, 'utf8');

    const input = {
        language: 'Solidity',
        sources: { 'MockERC20.sol': { content: source } },
        settings: { outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object'] } } }
    };

    const output = JSON.parse(solc.compile(JSON.stringify(input)));
    const contractJson = output.contracts['MockERC20.sol']['MockERC20'];
    const bytecode = contractJson.evm.bytecode.object;
    const abi = contractJson.abi;
    console.log("✓ Contract compiled successfully.");

    // 2. Setup Ethers provider & wallet
    const provider = new ethers.JsonRpcProvider(rpcUrl);
    const wallet = new ethers.Wallet(privateKey, provider);
    const payerWallet = new ethers.Wallet(payerPrivateKey);
    console.log(`Deployer Wallet Address: ${wallet.address}`);
    console.log(`Payer Wallet Address (Recipient): ${payerWallet.address}`);

    // 3. Deploy contract
    const factory = new ethers.ContractFactory(abi, bytecode, wallet);
    
    const initialSupply = ethers.parseUnits("1000000", 18); // 1 million tUSDC
    console.log(`Deploying token with initial supply: 1,000,000 to ${payerWallet.address}...`);

    const feeData = await provider.getFeeData();
    const contract = await factory.deploy("Test USDC", "tUSDC", payerWallet.address, initialSupply, {
        maxFeePerGas: feeData.maxFeePerGas,
        maxPriorityFeePerGas: feeData.maxPriorityFeePerGas
    });
    
    const txHash = contract.deploymentTransaction().hash;
    console.log(`Transaction submitted! Hash: ${txHash}`);
    console.log("Waiting for confirmation...");

    await contract.waitForDeployment();
    const deployedAddress = await contract.getAddress();
    
    console.log("\n✓ Contract deployed successfully!");
    console.log(`Deployed Contract Address: ${deployedAddress}`);
    console.log(`Deploy Transaction Hash: ${txHash}`);

    // 4. Update .env file
    updateEnv(deployedAddress);
}

main().catch(console.error);
