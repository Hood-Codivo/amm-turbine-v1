use anchor_lang::prelude::*;
use anchor_spl::{
    associated_token::AssociatedToken,
    token::{transfer, Mint, Token, TokenAccount, Transfer},
};
use constant_product_curve::{ConstantProduct, LiquidityPair};

use crate::{error::AmmError, state::Config};

#[derive(Accounts)]
pub struct Swap<'info> {
    #[account(mut)]
    pub user: Signer<'info>,
    pub mint_x: Box<Account<'info, Mint>>,
    pub mint_y: Box<Account<'info, Mint>>,
    #[account(
        has_one = mint_x,
        has_one = mint_y,
        seeds = [b"config", config.seed.to_le_bytes().as_ref()],
        bump = config.config_bump,
    )]
    pub config: Box<Account<'info, Config>>,
    #[account(
        mut,
        seeds = [b"lp", config.key().as_ref()],
        bump = config.lp_bump,
    )]
    pub mint_lp: Box<Account<'info, Mint>>,
    #[account(
        mut,
        associated_token::mint = mint_x,
        associated_token::authority = config,
    )]
    pub vault_x: Box<Account<'info, TokenAccount>>,
    #[account(
        mut,
        associated_token::mint = mint_y,
        associated_token::authority = config,
    )]
    pub vault_y: Box<Account<'info, TokenAccount>>,
    #[account(
        mut,
        associated_token::mint = mint_x,
        associated_token::authority = user,
    )]
    pub user_x: Box<Account<'info, TokenAccount>>,
    #[account(
        mut,
        associated_token::mint = mint_y,
        associated_token::authority = user,
    )]
    pub user_y: Box<Account<'info, TokenAccount>>,
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
    pub associated_token_program: Program<'info, AssociatedToken>,
}

impl<'info> Swap<'info> {
    pub fn swap(&mut self, is_x: bool, amount: u64, min: u64) -> Result<()> {
        require!(amount > 0, AmmError::InvalidAmount);
        let mut curve: ConstantProduct = ConstantProduct::init(
            self.vault_x.amount,
            self.vault_y.amount,
            self.mint_lp.supply,
            self.config.fee,
            Some(6),
        )
        .unwrap();

        let p: LiquidityPair = match is_x {
            true => LiquidityPair::X,
            false => LiquidityPair::Y,
        };

        let swap_result = curve
            .swap(p, amount, min)
            .map_err(|_| AmmError::SlippageLimitExceeded)?;

        self.deposit_tokens(is_x, swap_result.deposit)?;
        self.withdraw_tokens(is_x, swap_result.withdraw)
    }

    pub fn deposit_tokens(&self, is_x: bool, amount: u64) -> Result<()> {
        let (from, to): (AccountInfo<'info>, AccountInfo<'info>) = match is_x {
            true => (
                self.user_x.to_account_info(),
                self.vault_x.to_account_info(),
            ),
            false => (
                self.user_y.to_account_info(),
                self.vault_y.to_account_info(),
            ),
        };

        let cpi_accounts = Transfer {
            from,
            to,
            authority: self.user.to_account_info(),
        };

        let cpi_ctx = CpiContext::new(self.token_program.key(), cpi_accounts);

        transfer(cpi_ctx, amount)
    }

    pub fn withdraw_tokens(&self, is_x: bool, amount: u64) -> Result<()> {
        let (from, to): (AccountInfo<'info>, AccountInfo<'info>) = match is_x {
            true => (
                self.vault_y.to_account_info(),
                self.user_y.to_account_info(),
            ),
            false => (
                self.vault_x.to_account_info(),
                self.user_x.to_account_info(),
            ),
        };

        let seed = self.config.seed.to_le_bytes();
        let signer_seeds: &[&[&[u8]]] = &[&[b"config", seed.as_ref(), &[self.config.config_bump]]];

        let cpi_accounts = Transfer {
            from,
            to,
            authority: self.config.to_account_info(),
        };

        let cpi_ctx =
            CpiContext::new_with_signer(self.token_program.key(), cpi_accounts, signer_seeds);

        transfer(cpi_ctx, amount)
    }
}
