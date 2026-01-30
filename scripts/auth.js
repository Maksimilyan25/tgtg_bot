#!/usr/bin/env node

import readline from 'readline';

import { loadTokens } from '../src/api/tokenManager.js';
import { addAccountInteractive, reloginAccountInteractive, removeAccountInteractive, removeAccountNonInteractive } from '../src/utils/accountSetup.js';

function prompt(question) {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    return new Promise(resolve => rl.question(question, answer => { rl.close(); resolve(answer.trim()); }));
}

function printDivider() {
    console.log('======================================================');
}

const STATUS_CODES = {
    INVALID: 0,
    WAIT: 1,
    OK: 2
};

function formatStatus(token) {
    const now = Date.now();
    if (token.invalid) {
        return { code: STATUS_CODES.INVALID, label: '❌ Недействителен' };
    }
    if (token.resetAt && new Date(token.resetAt).getTime() > now) {
        return { code: STATUS_CODES.WAIT, label: '⏳ Ожидание сброса' };
    }
    return { code: STATUS_CODES.OK, label: '✅ OK' };
}

function printAccounts(tokens) {
    console.log('\nСписок аккаунтов:');
    if (!tokens.length) {
        console.log('  (пусто)');
        return;
    }

    tokens.forEach((token, index) => {
        const status = formatStatus(token);
        console.log(`${String(index + 1).padStart(2, ' ')} | ${token.id} | ${status.label} (${status.code})`);
    });
}

function handleList(tokens) {
    printAccounts(tokens);
    const active = tokens.filter(t => formatStatus(t).code === STATUS_CODES.OK);
    console.log(`\nАктивных аккаунтов: ${active.length} из ${tokens.length}`);
}

function handleListJson(tokens) {
    const active = tokens.filter(t => formatStatus(t).code === STATUS_CODES.OK);
    // Возвращаем данные в формате JSON для Telegram бота
    const accountsData = tokens.map(token => {
        const status = formatStatus(token);
        return {
            id: token.id,
            status: status.label,
            status_code: status.code
        };
    });
    return {
        success: true,
        accounts: accountsData,
        active_count: active.length,
        total_count: tokens.length
    };
}

function parseArgs(argv) {
    const args = argv.slice(2);
    const result = {
        action: null,
        params: {}
    };

    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--help' || args[i] === '-h') {
            result.action = 'help';
            return result;
        }
        if (args[i] === '--list') {
            result.action = 'list';
            if (args[i + 1] === '--json') {
                result.params.json = true;
                i++;
            }
            return result;
        }
        if (args[i] === '--add') {
            result.action = 'add';
            return result;
        }
        if (args[i] === '--relogin') {
            result.action = 'relogin';
            return result;
        }
        if (args[i] === '--remove') {
            result.action = 'remove';
            if (args[i + 1] && !args[i + 1].startsWith('--')) {
                result.params.accountId = args[i + 1];
                i++;
            }
            if (args[i + 1] === '--force') {
                result.params.force = true;
                i++;
            }
            return result;
        }
    }

    return result;
}

function printHelp() {
    printDivider();
    console.log('Скрипт управления аккаунтами Qwen');
    printDivider();
    console.log('Опции:');
    console.log('  --list [--json]      Показать список аккаунтов и статусы');
    console.log('  --add                Добавить новый аккаунт');
    console.log('  --relogin            Перелогинить аккаунт с истекшим токеном');
    console.log('  --remove <ID> [--force] Удалить аккаунт (--force - без подтверждения)');
    console.log('Без опций запускается интерактивное меню.');
    printDivider();
}

async function runCliAction(action, params) {
    if (action === 'help') {
        printHelp();
        return;
    }

    if (action === 'list') {
        const tokens = loadTokens();
        if (params && params.json) {
            const result = handleListJson(tokens);
            console.log(JSON.stringify(result));
        } else {
            handleList(tokens);
        }
        return;
    }

    if (action === 'add') {
        await addAccountInteractive();
        return;
    }

    if (action === 'relogin') {
        await reloginAccountInteractive();
        return;
    }

    if (action === 'remove') {
        const result = await removeAccountNonInteractive(params.accountId, params.force);
        console.log(JSON.stringify(result));
        return;
    }
}

async function runInteractiveMenu() {
    while (true) {
        const tokens = loadTokens();
        printDivider();
        printAccounts(tokens);
        printDivider();
        console.log('Меню:');
        console.log('1 - Добавить новый аккаунт');
        console.log('2 - Перелогинить аккаунт с истекшим токеном');
        console.log('3 - Удалить аккаунт');
        console.log('4 - Показать список и статусы');
        console.log('5 - Выход');
        const choice = await prompt('Ваш выбор (Enter = 5): ');
        const normalized = choice || '5';

        if (normalized === '1') {
            await addAccountInteractive();
        } else if (normalized === '2') {
            await reloginAccountInteractive();
        } else if (normalized === '3') {
            await removeAccountInteractive();
        } else if (normalized === '4') {
            handleList(tokens);
            await prompt('\nНажмите Enter, чтобы вернуться в меню...');
        } else if (normalized === '5') {
            console.log('Выход из скрипта.');
            break;
        }
    }
}

(async () => {
    const action = parseArgs(process.argv);
    if (action.action) {
        await runCliAction(action.action, action.params);
        return;
    }

    await runInteractiveMenu();
})();
