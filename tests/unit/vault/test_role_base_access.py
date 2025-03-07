import ape
from utils.constants import ROLES, WEEK, StrategyChangeType
from utils.utils import days_to_secs


# STRATEGY MANAGEMENT


def test_add_strategy__no_add_strategy_manager__reverts(vault, create_strategy, bunny):
    new_strategy = create_strategy(vault)
    with ape.reverts("not allowed"):
        vault.add_strategy(new_strategy, sender=bunny)


def test_add_strategy__add_strategy_manager(vault, create_strategy, gov, bunny):
    # We temporarily give bunny the role of STRATEGY_MANAGER
    vault.set_role(bunny.address, ROLES.ADD_STRATEGY_MANAGER, sender=gov)

    new_strategy = create_strategy(vault)
    tx = vault.add_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.ADDED


def test_revoke_strategy__no_revoke_strategy_manager__reverts(vault, strategy, bunny):
    with ape.reverts("not allowed"):
        vault.revoke_strategy(strategy, sender=bunny)


def test_revoke_strategy__revoke_strategy_manager(vault, strategy, gov, bunny):
    # We temporarily give bunny the role of STRATEGY_MANAGER
    vault.set_role(bunny.address, ROLES.REVOKE_STRATEGY_MANAGER, sender=gov)

    tx = vault.revoke_strategy(strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED


def test_force_revoke_strategy__no_revoke_strategy_manager__reverts(
    vault, strategy, create_strategy, bunny
):

    with ape.reverts("not allowed"):
        vault.force_revoke_strategy(strategy, sender=bunny)


def test_force_revoke_strategy__revoke_strategy_manager(
    vault, strategy, create_strategy, gov, bunny
):
    # We temporarily give bunny the role of STRATEGY_MANAGER
    vault.set_role(bunny.address, ROLES.FORCE_REVOKE_MANAGER, sender=gov)

    tx = vault.force_revoke_strategy(strategy, sender=bunny)

    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED


# ACCOUNTING MANAGEMENT


def test_set_minimum_total_idle__no_min_idle_manager__reverts(bunny, vault):
    minimum_total_idle = 1
    with ape.reverts("not allowed"):
        vault.set_minimum_total_idle(minimum_total_idle, sender=bunny)


def test_set_minimum_total_idle__min_idle_manager(gov, vault, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_role(bunny.address, ROLES.MINIMUM_IDLE_MANAGER, sender=gov)

    assert vault.minimum_total_idle() == 0
    minimum_total_idle = 1
    vault.set_minimum_total_idle(minimum_total_idle, sender=bunny)
    assert vault.minimum_total_idle() == 1


def test_update_max_debt__no_max_debt_manager__reverts(vault, strategy, bunny):
    assert vault.strategies(strategy).max_debt == 0
    max_debt_for_strategy = 1
    with ape.reverts("not allowed"):
        vault.update_max_debt_for_strategy(
            strategy, max_debt_for_strategy, sender=bunny
        )


def test_update_max_debt__max_debt_manager(gov, vault, strategy, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_role(bunny.address, ROLES.MAX_DEBT_MANAGER, sender=gov)

    assert vault.strategies(strategy).max_debt == 0
    max_debt_for_strategy = 1
    vault.update_max_debt_for_strategy(strategy, max_debt_for_strategy, sender=bunny)
    assert vault.strategies(strategy).max_debt == 1


def test_set_deposit_limit__no_deposit_limit_manager__reverts(bunny, vault):
    deposit_limit = 1
    with ape.reverts("not allowed"):
        vault.set_deposit_limit(deposit_limit, sender=bunny)


def test_set_deposit_limit__deposit_limit_manager(gov, vault, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_role(bunny.address, ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    deposit_limit = 1
    assert vault.deposit_limit() != deposit_limit
    vault.set_deposit_limit(deposit_limit, sender=bunny)
    assert vault.deposit_limit() == deposit_limit


# SWEEPER


def test_sweep__no_sweeper__reverts(vault, strategy, bunny):
    with ape.reverts("not allowed"):
        vault.process_report(strategy, sender=bunny)


def test_sweep__sweeper(
    gov,
    asset,
    vault,
    bunny,
    airdrop_asset,
    mint_and_deposit_into_vault,
):
    # We temporarily give bunny the role of ACCOUNTING_MANAGER
    vault.set_role(bunny.address, ROLES.SWEEPER, sender=gov)

    vault_balance = 10**22
    asset_airdrop = vault_balance // 10
    mint_and_deposit_into_vault(vault, gov, vault_balance)

    airdrop_asset(gov, asset, vault, asset_airdrop)

    tx = vault.sweep(asset.address, sender=bunny)
    event = list(tx.decode_logs(vault.Sweep))

    assert len(event) == 1
    assert event[0].token == asset.address
    assert event[0].amount == asset_airdrop


# DEBT_MANAGER


def test_update_debt__no_debt_manager__reverts(vault, gov, strategy, bunny):
    with ape.reverts("not allowed"):
        vault.update_debt(strategy, 10**18, sender=bunny)


def test_update_debt__debt_manager(
    gov, mint_and_deposit_into_vault, vault, strategy, bunny
):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_role(bunny.address, ROLES.DEBT_MANAGER, sender=gov)

    # Provide vault with funds
    mint_and_deposit_into_vault(vault, gov, 10**18, 10**18 // 2)

    max_debt_for_strategy = 1
    vault.update_max_debt_for_strategy(strategy, max_debt_for_strategy, sender=gov)

    tx = vault.update_debt(strategy, max_debt_for_strategy, sender=bunny)

    event = list(tx.decode_logs(vault.DebtUpdated))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == 0
    assert event[0].new_debt == 1


# EMERGENCY_MANAGER


def test_shutdown_vault__no_emergency_manager__reverts(vault, bunny):
    with ape.reverts("not allowed"):
        vault.shutdown_vault(sender=bunny)


def test_shutdown_vault__emergency_manager(gov, vault, bunny):
    # We temporarily give bunny the role of EMERGENCY_MANAGER
    vault.set_role(bunny.address, ROLES.EMERGENCY_MANAGER, sender=gov)

    assert vault.shutdown() == False
    tx = vault.shutdown_vault(sender=bunny)

    assert vault.shutdown() == True
    event = list(tx.decode_logs(vault.Shutdown))
    assert len(event) == 1
    # lets ensure that we give the EMERGENCY_MANAGER DEBT_MANAGER permissions after shutdown
    # EMERGENCY_MANAGER=4096 DEBT_MANGER=64 -> binary or operation should give us 4160 (10001000000)
    assert vault.roles(bunny) == 4160


# REPORTING_MANAGER


def test_process_report__no_reporting_manager__reverts(vault, strategy, bunny):
    with ape.reverts("not allowed"):
        vault.process_report(strategy, sender=bunny)


def test_process_report__reporting_manager(
    gov,
    vault,
    asset,
    airdrop_asset,
    add_debt_to_strategy,
    strategy,
    bunny,
    mint_and_deposit_into_vault,
):
    # We temporarily give bunny the role of ACCOUNTING_MANAGER
    vault.set_role(bunny.address, ROLES.REPORTING_MANAGER, sender=gov)

    # Provide liquidity into vault
    mint_and_deposit_into_vault(vault, gov, 10**18, 10**18 // 2)
    # add debt to strategy
    add_debt_to_strategy(gov, strategy, vault, 2)
    # airdrop gain to strategy
    airdrop_asset(gov, asset, strategy, 1)

    tx = vault.process_report(strategy.address, sender=bunny)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == 1
    assert event[0].loss == 0


# SET_ACCOUNTANT_MANAGER


def test_set_accountant__no_accountant_manager__reverts(bunny, vault):
    with ape.reverts("not allowed"):
        vault.set_accountant(bunny, sender=bunny)


def test_set_accountant__accountant_manager(gov, vault, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_role(bunny.address, ROLES.ACCOUNTANT_MANAGER, sender=gov)

    assert vault.accountant() != bunny
    vault.set_accountant(bunny, sender=bunny)
    assert vault.accountant() == bunny


# QUEUE MANAGER


def test_set_queue_manager__no_queue_manager__reverts(bunny, vault):
    with ape.reverts("not allowed"):
        vault.set_queue_manager(bunny, sender=bunny)


def test_set_queue_manager__queue_manager(gov, vault, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_role(bunny.address, ROLES.QUEUE_MANAGER, sender=gov)

    assert vault.queue_manager() != bunny
    vault.set_queue_manager(bunny, sender=bunny)
    assert vault.queue_manager() == bunny


# PROFIT UNLOCK MANAGER


def test_set_profit_unlcok__no_profit_unlock_manager__reverts(bunny, vault):
    with ape.reverts("not allowed"):
        vault.set_profit_max_unlock_time(WEEK // 2, sender=bunny)


def test_set_profit_unlcok__profit_unlcok_manager(gov, vault, bunny):
    # We temporarily give bunny the role of profit unlock manager
    vault.set_role(bunny.address, ROLES.PROFIT_UNLOCK_MANAGER, sender=gov)

    time = WEEK // 2
    assert vault.profit_max_unlock_time() != time
    vault.set_profit_max_unlock_time(time, sender=bunny)
    assert vault.profit_max_unlock_time() == time
