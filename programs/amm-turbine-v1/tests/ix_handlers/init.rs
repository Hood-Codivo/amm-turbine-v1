use {
    anchor_lang::{
        prelude::Pubkey, solana_program::instruction::Instruction, system_program, InstructionData,
        ToAccountMetas,
    },
    anchor_spl::{associated_token, token},
    litesvm::LiteSVM,
    solana_keypair::Keypair,
    solana_signer::Signer,
};

pub fn create_initialise_ix(
    _svm: &mut LiteSVM,
    payer: &Keypair,
    mint_x: Pubkey,
    mint_y: Pubkey,
    config: Pubkey,
    mint_lp: Pubkey,
    vault_x: Pubkey,
    vault_y: Pubkey,
) -> Instruction {
    let maker = payer.pubkey();

    Instruction::new_with_bytes(
        amm_turbine_v1::id(),
        &amm_turbine_v1::instruction::Initialize {
            seed: 123,
            fee: 30,
            authority: Some(maker),
        }
        .data(),
        amm_turbine_v1::accounts::Initialize {
            initializer: maker,
            mint_x,
            mint_y,
            mint_lp,
            vault_x,
            vault_y,
            config,
            token_program: token::ID,
            associated_token_program: associated_token::ID,
            system_program: system_program::ID,
        }
        .to_account_metas(None),
    )
}
