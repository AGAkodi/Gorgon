const path = require('path');
const fs = require('fs');
const solc = require('solc');
const { ethers } = require('ethers');
require('dotenv').config();

function updateEnv(deployedAddress) {
    const envPath = path.resolve(__dirname, '.env');
    let envContent = fs.readFileSync(envPath, 'utf8');
    
    const regex = /^ATTESTATION_CONTRACT_ADDRESS=.*$/m;
    if (regex.test(envContent)) {
        envContent = envContent.replace(regex, `ATTESTATION_CONTRACT_ADDRESS=${deployedAddress}`);
    } else {
        envContent += `\nATTESTATION_CONTRACT_ADDRESS=${deployedAddress}`;
    }
    fs.writeFileSync(envPath, envContent, 'utf8');
    console.log(`\n[Env Config] Updated ATTESTATION_CONTRACT_ADDRESS in .env to ${deployedAddress}`);
}

async function main() {
    console.log("=== VetraAttestation Contract Deployment ===");
    
    const rpcUrl = process.env.X_LAYER_TESTNET_RPC_URL;
    const privateKey = process.env.ATTESTATION_WALLET_PRIVATE_KEY;

    if (!rpcUrl || !privateKey) {
        console.error("\nError: X_LAYER_TESTNET_RPC_URL or ATTESTATION_WALLET_PRIVATE_KEY is not defined in .env");
        console.error("Please populate these variables in your .env file and run the script again.");
        process.exit(1);
    }

    // 1. Compile contract
    console.log("\n1. Compiling VetraAttestation.sol...");
    const contractPath = path.resolve(__dirname, 'attestation', 'contract', 'VetraAttestation.sol');
    if (!fs.existsSync(contractPath)) {
        console.error(`Error: Contract file not found at ${contractPath}`);
        process.exit(1);
    }
    const source = fs.readFileSync(contractPath, 'utf8');

    const input = {
        language: 'Solidity',
        sources: {
            'VetraAttestation.sol': {
                content: source
            }
        },
        settings: {
            outputSelection: {
                '*': {
                    '*': ['abi', 'evm.bytecode.object']
                }
            }
        }
    };

    const output = JSON.parse(solc.compile(JSON.stringify(input)));

    if (output.errors) {
        let hasError = false;
        for (const error of output.errors) {
            console.error(error.formattedMessage);
            if (error.severity === 'error') {
                hasError = true;
            }
        }
        if (hasError) {
            console.error("Compilation failed.");
            process.exit(1);
        }
    }

    const contractJson = output.contracts['VetraAttestation.sol']['VetraAttestation'];
    const bytecode = contractJson.evm.bytecode.object;
    const abi = contractJson.abi;
    console.log("✓ Contract compiled successfully.");

    // 2. Setup Ethers provider & wallet
    console.log("\n2. Connecting to network and checking balance...");
    const provider = new ethers.JsonRpcProvider(rpcUrl);
    const wallet = new ethers.Wallet(privateKey, provider);
    console.log(`Deployer Wallet Address: ${wallet.address}`);

    const balance = await provider.getBalance(wallet.address);
    console.log(`Deployer Wallet Balance: ${ethers.formatEther(balance)} OKB`);
    if (balance === 0n) {
        console.error("Error: Wallet balance is 0 OKB. Cannot send deployment transaction.");
        process.exit(1);
    }

    // 3. Deploy contract
    console.log("\n3. Sending deployment transaction...");
    const factory = new ethers.ContractFactory(abi, bytecode, wallet);
    
    // Explicitly estimate gas and specify gas parameters to ensure smooth testnet tx inclusion
    const feeData = await provider.getFeeData();
    const deployTx = await factory.getDeployTransaction();
    const estimatedGas = await provider.estimateGas(deployTx);
    
    // Use estimated gas with a 20% safety buffer
    const gasLimit = (estimatedGas * 120n) / 100n;

    console.log(`Estimated Gas: ${estimatedGas.toString()} units`);
    console.log(`Max Fee Per Gas: ${feeData.maxFeePerGas ? ethers.formatUnits(feeData.maxFeePerGas, 'gwei') : 'N/A'} gwei`);
    
    const contract = await factory.deploy({
        gasLimit,
        maxFeePerGas: feeData.maxFeePerGas,
        maxPriorityFeePerGas: feeData.maxPriorityFeePerGas
    });

    const txHash = contract.deploymentTransaction().hash;
    console.log(`Transaction submitted! Hash: ${txHash}`);
    console.log("Waiting for confirmation (usually takes 5-15 seconds)...");

    await contract.waitForDeployment();

    const deployedAddress = await contract.getAddress();
    console.log("\n✓ Contract deployed successfully!");
    console.log(`Deployed Contract Address: ${deployedAddress}`);
    console.log(`Deploy Transaction Hash: ${txHash}`);
    
    console.log("\nExplorer Links:");
    console.log(`- Transaction: https://www.oklink.com/xlayer-test/tx/${txHash}`);
    console.log(`- Address:     https://www.oklink.com/xlayer-test/address/${deployedAddress}`);

    // 4. Update .env file
    updateEnv(deployedAddress);
}

main().catch((error) => {
    console.error("\nUnexpected error during deployment:", error);
    process.exit(1);
});
