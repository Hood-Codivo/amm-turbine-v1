use {
    anchor_lang::{prelude::Pubkey, solana_program::instruction::Instruction},
    anchor_spl::associated_token,
    litesvm::{types::TransactionResult, LiteSVM},
    litesvm_token::CreateMint,
    solana_keypair::Keypair,
    solana_message::{Message, VersionedMessage},
    solana_signer::Signer,
    solana_transaction::versioned::VersionedTransaction,
};

mod ix_handlers;
use ix_handlers::*;

fn send(
    svm: &mut LiteSVM,
    ixs: &[Instruction],
    payer: &Keypair,
    signers: &[&Keypair],
) -> TransactionResult {
    svm.expire_blockhash();
    let blockhash = svm.latest_blockhash();
    let msg = Message::new_with_blockhash(ixs, Some(&payer.pubkey()), &blockhash);
    let tx = VersionedTransaction::try_new(VersionedMessage::Legacy(msg), signers).unwrap();
    svm.send_transaction(tx)
}

fn assert_tx_ok(res: TransactionResult) {
    if let Err(err) = &res {
        eprintln!("transaction error: {:?}", err.err);
        eprintln!("{}", err.meta.pretty_logs());
    }
    assert!(res.is_ok());
}

fn setup() -> (
    LiteSVM,
    Keypair,
    Pubkey,
    Pubkey,
    Pubkey,
    Pubkey,
    Pubkey,
    Pubkey,
) {
    let program_id = amm_turbine_v1::id();
    let payer = Keypair::new();
    let mut svm = LiteSVM::new();
    svm.add_program_from_file(
        program_id,
        concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../target/deploy/amm_turbine_v1.so"
        ),
    )
    .unwrap();
    svm.airdrop(&payer.pubkey(), 1_000_000_000).unwrap();

    // Create two mints (Mint A and Mint B) with 6 decimal places and maker as the authority
    // This done using litesvm-token's CreateMint utility which the mint in the LiteSVM environment
    let mint_x = CreateMint::new(&mut svm, &payer)
        .decimals(6)
        .authority(&payer.pubkey())
        .send()
        .unwrap();

    let mint_y = CreateMint::new(&mut svm, &payer)
        .decimals(6)
        .authority(&payer.pubkey())
        .send()
        .unwrap();

    let config = Pubkey::find_program_address(&[b"config", &123u64.to_le_bytes()], &program_id).0;
    let mint_lp = Pubkey::find_program_address(&[b"lp", config.as_ref()], &program_id).0;

    // Derive the PDA for the vault associted token account using the config PDA AND Mint A
    let vault_x = associated_token::get_associated_token_address(&config, &mint_x);
    let vault_y = associated_token::get_associated_token_address(&config, &mint_y);

    (
        svm, payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y,
    )
}

#[test]
fn test_initialize() {
    let (mut svm, payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y) = setup();

    let init_ix = create_initialise_ix(
        &mut svm, &payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y,
    );
    let res = send(&mut svm, &[init_ix], &payer, &[&payer]);
    assert_tx_ok(res);
}

#[test]
fn test_deposit() {
    let (mut svm, payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y) = setup();

    let init_ix = create_initialise_ix(
        &mut svm, &payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y,
    );
    let deposit_ix = create_deposit_ix(
        &mut svm, &payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y,
    );

    let res = send(&mut svm, &[init_ix, deposit_ix], &payer, &[&payer]);
    assert_tx_ok(res);
}

#[test]
fn test_withdraw() {
    let (mut svm, payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y) = setup();

    let init_ix = create_initialise_ix(
        &mut svm, &payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y,
    );
    let deposit_ix = create_deposit_ix(
        &mut svm, &payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y,
    );
    let withdraw_ix = create_withdraw_ix(
        &mut svm, &payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y,
    );

    let res = send(
        &mut svm,
        &[init_ix, deposit_ix, withdraw_ix],
        &payer,
        &[&payer],
    );
    assert_tx_ok(res);
}

#[test]
fn test_swap() {
    let (mut svm, payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y) = setup();

    let init_ix = create_initialise_ix(
        &mut svm, &payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y,
    );
    let deposit_ix = create_deposit_ix(
        &mut svm, &payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y,
    );
    let swap_ix = create_swap_ix(
        &mut svm, &payer, mint_x, mint_y, config, mint_lp, vault_x, vault_y,
    );

    let res = send(&mut svm, &[init_ix, deposit_ix, swap_ix], &payer, &[&payer]);
    assert_tx_ok(res);
}
