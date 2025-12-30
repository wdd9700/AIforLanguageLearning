
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const chalk = require('chalk'); // 需要安装 chalk 或使用简单的 console.log

// 简单的颜色输出工具
const colors = {
  red: (msg) => `\x1b[31m${msg}\x1b[0m`,
  green: (msg) => `\x1b[32m${msg}\x1b[0m`,
  yellow: (msg) => `\x1b[33m${msg}\x1b[0m`,
  blue: (msg) => `\x1b[34m${msg}\x1b[0m`,
};

console.log(colors.blue('=== MMLS Python Environment Check ==='));

// 1. 读取配置中的 Python 路径
let pythonPath = 'python'; // 默认
try {
  const envPath = path.join(__dirname, '../src/config/env.ts');
  if (fs.existsSync(envPath)) {
    const envContent = fs.readFileSync(envPath, 'utf-8');
    const match = envContent.match(/pythonPath:\s*process\.env\.PYTHON_PATH\s*\|\|\s*['"](.+?)['"]/);
    if (match && match[1]) {
      pythonPath = match[1];
    }
  }
} catch (e) {
  console.warn(colors.yellow('Warning: Could not read env.ts, using default "python" command.'));
}

console.log(`Checking Python at: ${colors.yellow(pythonPath)}`);

// 2. 检查 Python 版本
try {
  const versionOutput = execSync(`"${pythonPath}" --version`).toString().trim();
  console.log(`Detected: ${versionOutput}`);
  
  const versionMatch = versionOutput.match(/Python (\d+)\.(\d+)\.(\d+)/);
  if (versionMatch) {
    const major = parseInt(versionMatch[1]);
    const minor = parseInt(versionMatch[2]);
    
    // 检查是否在 3.10 - 3.12 之间
    if (major === 3 && (minor >= 10 && minor <= 12)) {
      console.log(colors.green('✓ Python version is compatible (3.10 - 3.12).'));
    } else {
      console.error(colors.red(`✗ Incompatible Python version: ${versionOutput}`));
      console.error(colors.red('  Required: Python 3.10, 3.11, or 3.12'));
      console.error(colors.yellow('  Reason: torch and webrtcvad do not support Python 3.14 yet.'));
      console.error(colors.yellow('  Action: Please install Python 3.10/3.11 and update .env or src/config/env.ts'));
      process.exit(1);
    }
  }
} catch (e) {
  console.error(colors.red(`✗ Failed to execute python: ${e.message}`));
  process.exit(1);
}

// 3. 检查关键依赖
const requiredModules = ['torch', 'torchaudio', 'faster_whisper', 'webrtcvad', 'TTS', 'numpy'];
console.log(colors.blue('\nChecking required modules...'));

let missingModules = [];

for (const module of requiredModules) {
  try {
    execSync(`"${pythonPath}" -c "import ${module}"`, { stdio: 'ignore' });
    console.log(`${colors.green('✓')} ${module}`);
  } catch (e) {
    console.log(`${colors.red('✗')} ${module}`);
    missingModules.push(module);
  }
}

if (missingModules.length > 0) {
  console.error(colors.red('\nMissing required Python modules:'));
  missingModules.forEach(m => console.error(`  - ${m}`));
  console.log(colors.yellow('\nPlease run the following command to install dependencies:'));
  
  // 特殊处理 webrtcvad
  const installList = missingModules.map(m => m === 'webrtcvad' ? 'webrtcvad-wheels' : m).join(' ');
  console.log(colors.blue(`  "${pythonPath}" -m pip install ${installList}`));
  process.exit(1);
}

console.log(colors.green('\n✓ All environment checks passed! Ready to start services.'));
process.exit(0);
