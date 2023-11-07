import beaker as bk
import pyteal as pt
from pyteal import *
from beaker.lib.storage import BoxMapping


class CampaignRecord(abi.NamedTuple):
    name: abi.Field[abi.String]
    desc: abi.Field[abi.String]
    goal: abi.Field[abi.Uint64]
    amount_raised: abi.Field[abi.Uint64]
    creator: abi.Field[abi.Address]
    status: abi.Field[abi.Bool]


class MyState:
    totalCampaign = bk.GlobalStateValue(pt.TealType.uint64)
    owner = bk.GlobalStateValue(
        stack_type=pt.TealType.bytes, default=pt.Txn.sender(), static=True)
    camp_records = BoxMapping(abi.Address, CampaignRecord)

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
def add_campaign(new_member: abi.Address ) -> pt.Expr:
    #new_total = app.state.totalCampaignincrement(v.get())
    return pt.Seq(
        (name := abi.String()).set("Gaza"),
        (desc := abi.String()).set("A new project"),
        (goal := abi.Uint64()).set(pt.Int(110)),
        (amount_raised := abi.Uint64()).set(pt.Int(0)),
        (creator := abi.Address()).set(new_member),
        (status := abi.Bool()).set(pt.Int(0)),
        (cr := CampaignRecord()).set(name, desc, goal, amount_raised, creator, status),
        app.state.camp_records[new_member].set(cr),
        app.state.totalCampaign.increment()
        )


@app.external(read_only=True, authorize=is_owner)
def approveCampaign(member: abi.Address, *, output: CampaignRecord) -> Expr:
    existing_camp = CampaignRecord()
    new_status = abi.Bool()

    return pt.Seq(
        existing_camp.decode(app.state.camp_records[member.get()].get()),
        new_status.set(Int(1)),
        (name := abi.String()).set(existing_camp.name),
        (desc := abi.String()).set(existing_camp.desc),
        (goal := abi.Uint64()).set(existing_camp.goal),
        (amount_raised := abi.Uint64()).set(existing_camp.amount_raised),
        (creator := abi.Address()).set(existing_camp.creator),
        existing_camp.set(name, desc, goal, amount_raised, creator, new_status),
        app.state.camp_records[member.get()].set(existing_camp),
        app.state.camp_records[member.get()].store_into(output),
    )

@app.external(read_only=True)
def get_campaign(
    member: abi.Address, *, output: CampaignRecord
) -> pt.Expr:
    return app.state.camp_records[member].store_into(output)

if __name__ == "__main__":
    spec = app.build()
    spec.export("artifacts")  
