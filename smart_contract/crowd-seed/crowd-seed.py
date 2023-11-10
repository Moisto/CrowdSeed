import beaker as bk
import pyteal as pt
from pyteal import *
from beaker.lib.storage import BoxMapping


class CampaignRecord(abi.NamedTuple):
    name: abi.Field[abi.String]
    desc: abi.Field[abi.String]
    goal: abi.Field[abi.Uint64]
    amount_raised: abi.Field[abi.Uint64]
    deadline: abi.Field[abi.Uint64]
    creator: abi.Field[abi.Address]
    status: abi.Field[abi.Bool]


class MyState:
    totalCampaign = bk.GlobalStateValue(pt.TealType.uint64)
    owner = bk.GlobalStateValue(
        stack_type=pt.TealType.bytes, default=pt.Txn.sender(), static=True)
    camp_records = BoxMapping(abi.String, CampaignRecord)

app = bk.Application("CrowdSeed", state=MyState())


@app.external
def bootstrap() -> pt.Expr:
    return pt.Seq(
        app.initialize_global_state()
    )

@Subroutine(pt.TealType.uint64)
def is_owner(acct: pt.Expr):
    # Only owner
    return pt.Txn.sender() == app.state.owner

@app.external(read_only=True, authorize=is_owner)
def read_owner(*, output: abi.Address) -> pt.Expr:
    return output.set(app.state.owner)
    

@app.external(read_only=True)
def read_campaigns(*, output: abi.Uint64) -> pt.Expr:
    return output.set(app.state.totalCampaign)

@app.external
def add_campaign(new_camp: abi.String, name: abi.String, desc: abi.String, goal: abi.Uint64, deadline: abi.Uint64) -> pt.Expr:
    #new_total = app.state.totalCampaignincrement(v.get())
    return pt.Seq(
        #Assert(Global.latest_timestamp() >= deadline.get(), comment="Time should be in future"),
        (name := abi.String()).set(name),
        (desc := abi.String()).set(desc),
        (goal := abi.Uint64()).set(goal),
        (amount_raised := abi.Uint64()).set(pt.Int(0)),
        (deadline := abi.Uint64()).set(deadline),
        (creator := abi.Address()).set(Txn.sender()),
        (status := abi.Bool()).set(pt.Int(0)),
        (cr := CampaignRecord()).set(name, desc, goal, amount_raised, deadline, creator, status),
        app.state.camp_records[new_camp.get()].set(cr),
        app.state.totalCampaign.increment()
        )


@app.external(read_only=True, authorize=is_owner)
def approveCampaign(new_camp: abi.String, *, output: CampaignRecord) -> Expr:
    existing_camp = CampaignRecord()
    new_status = abi.Bool()

    return pt.Seq(
        existing_camp.decode(app.state.camp_records[new_camp.get()].get()),
        new_status.set(Int(1)),
        (name := abi.String()).set(existing_camp.name),
        (desc := abi.String()).set(existing_camp.desc),
        (goal := abi.Uint64()).set(existing_camp.goal),
        (amount_raised := abi.Uint64()).set(existing_camp.amount_raised),
        (deadline := abi.Uint64()).set(existing_camp.deadline),
        (creator := abi.Address()).set(existing_camp.creator),
        existing_camp.set(name, desc, goal, amount_raised, deadline, creator, new_status),
        app.state.camp_records[new_camp.get()].set(existing_camp),
        app.state.camp_records[new_camp.get()].store_into(output),
    )

@app.external(read_only=True)
def get_campaign(
    new_camp: abi.String, *, output: CampaignRecord
) -> pt.Expr:
    return app.state.camp_records[new_camp.get()].store_into(output)


@app.external
def send_algo_from_escrow(
    receiver: pt.abi.Account,
    amount: pt.abi.Uint64
) -> pt.Expr:
    return pt.InnerTxnBuilder.Execute({
        # You can do some assertion, like checking if the receiver is a particular address
        pt.TxnField.type_enum: pt.TxnType.Payment,
        pt.TxnField.receiver: receiver.address(),
        pt.TxnField.amount: amount.get()
    })

@app.external
def fund_campaign(
    txn: pt.abi.PaymentTransaction,
    new_camp: abi.String,
) -> pt.Expr:
    """
    Fund projects with Algos.

   :param pt.abi.PaymentTransaction txn: The payment transaction to fund the escrow address.
   :rtype: pt.Expr
    """
    existing_camp = CampaignRecord()
    existing_camp.decode(app.state.camp_records[new_camp.get()].get())
    return pt.Seq(
        pt.Assert(
            txn.get().amount() > pt.Int(0),
            txn.get().receiver() == pt.Global.current_application_address(),
            txn.get().type_enum() == pt.TxnType.Payment,
            comment="Invalid amount, receiver or type_enum."
        ),
        (name := abi.String()).set(existing_camp.name),
        (desc := abi.String()).set(existing_camp.desc),
        (goal := abi.Uint64()).set(existing_camp.goal),
        (deadline := abi.Uint64()).set(existing_camp.deadline),
        (creator := abi.Address()).set(existing_camp.creator),
        (status := abi.Bool()).set(existing_camp.status),
        (amount_raised := abi.Uint64()).set(existing_camp.amount_raised),
        amount_raised.set(amount_raised.get() + txn.get().amount()),
        existing_camp.set(name, desc, goal, amount_raised, deadline, creator, status),
        app.state.camp_records[new_camp.get()].set(existing_camp),
    )

@app.external
def fund_escrow_address(
    txn: pt.abi.PaymentTransaction
) -> pt.Expr:
    """
    Fund escrow address with Algos.

   :param pt.abi.PaymentTransaction txn: The payment transaction to fund the escrow address.
   :rtype: pt.Expr
    """
    return pt.Seq(
        pt.Assert(
            txn.get().amount() > pt.Int(0),
            txn.get().receiver() == pt.Global.current_application_address(),
            txn.get().type_enum() == pt.TxnType.Payment,
            comment="Invalid amount, receiver or type_enum."
        )
    )


if __name__ == "__main__":
    spec = app.build()
    spec.export("artifacts")  
