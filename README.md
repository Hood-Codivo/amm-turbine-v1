# AMM Flow Overview

This folder contains [amm-flow-diagram.pdf](./amm-flow-diagram.pdf), a visual guide for the AMM Turbine v1 pool flow.

## What Is An AMM?

An AMM, or Automated Market Maker, is a token pool that lets users trade against liquidity held in vaults. In this project, the pool holds two assets:

- Token A / `mint_x`
- Token B / `mint_y`

<img width="2880" height="1702" alt="image" src="https://github.com/user-attachments/assets/4d5a3bbd-876f-4266-ae22-104756c56f9b" />


The pool uses a constant-product curve, where the vault balances maintain the relationship `x * y = k`.

## Liquidity Flow

Liquidity providers deposit both Token A and Token B into the pool vaults:

```text
user_x + user_y -> vault_x + vault_y
```

After depositing, the AMM mints LP tokens to the user:

```text
(Token A, Token B) -> LP token
```

The LP token represents ownership of the pool share.

## Withdraw Flow

To withdraw liquidity, the user burns LP tokens:

```text
burn user_lp -> receive Token A + Token B
```

The AMM calculates the proportional amount of each token and transfers them from the vaults back to the user.

## Swap Flow

A swap sends one token into the pool and receives the other token out:

```text
Token A in -> Token B out
Token B in -> Token A out
```

The constant-product curve calculates the output amount and checks slippage using `min_amount_out`.

## Main Accounts

- `Config`: stores pool seed, authority, token mints, fee, lock state, and PDA bumps.
- `mint_x` / `mint_y`: the two token mints in the pool.
- `mint_lp`: the LP token mint.
- `vault_x` / `vault_y`: pool-owned token vaults.
- `user_x` / `user_y`: user token accounts.
- `user_lp`: user LP token account.

## PDA Rules

```text
config PDA = ["config", seed]
LP mint PDA = ["lp", config.key()]
```

Vault token accounts are associated token accounts owned by the `config` PDA.
