"""
Checks that the QoS demo seed (app/mock_data/seed_qos_demo.py) produces exactly
the profiles it documents, through the real reputation service.

Run: pytest backend/tests/test_reputation_seed.py -v
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base
from app.mock_data import seed_qos_demo as seed_mod
from app.services import reputation as rep

NOW = dt.datetime(2026, 10, 15, 12, 0, 0)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


@pytest.fixture()
def seeded(db):
    manifest = seed_mod.seed(db, NOW)
    return db, manifest


def _buyer(db, company):
    b = db.query(models.Buyer).filter(models.Buyer.company_name == company).one()
    return rep.buyer_profile(db, b.id, NOW)


def _agency(db, name):
    t = db.query(models.Transporter).filter(models.Transporter.name == name).one()
    return rep.transporter_profile(db, t.id, NOW)


def _frac(profile, key):
    i = {x["key"]: x for x in profile["indicators"]}[key]
    return (i["numerator"], i["denominator"]) if i["status"] == "measured" else None


def test_buyer_profiles(seeded):
    db, _ = seeded
    ae = _buyer(db, "AgriExport")
    assert ae["completed_outcomes"] == 15 and ae["sufficient_history"]
    assert _frac(ae, "pickup_reliability") == (14, 15) and _frac(ae, "terms_adherence") == (15, 15)

    ff = _buyer(db, "FreshFoods")
    assert _frac(ff, "pickup_reliability") == (11, 12) and _frac(ff, "terms_adherence") == (11, 12)
    assert ff["transaction_history"]["in_progress"] == 1          # the delivered txn awaiting an outcome

    gb = _buyer(db, "GreenBasket")
    assert _frac(gb, "pickup_reliability") == (8, 9)
    assert _frac(gb, "terms_adherence") == (7, 8)                  # 1 deviated record under review
    terms = {i["key"]: i for i in gb["indicators"]}["terms_adherence"]
    assert terms["excluded_under_review"] == 1

    km = _buyer(db, "Kisan Mandi Co.")
    assert _frac(km, "pickup_reliability") == (4, 7) and _frac(km, "terms_adherence") == (5, 8)
    assert "90" not in str(km)                                     # legacy seeded score never read

    rh = _buyer(db, "Raipur Fresh Hub")
    assert rh["sufficient_history"] and rh["completed_outcomes"] == 6
    assert _frac(rh, "pickup_reliability") is None and _frac(rh, "terms_adherence") is None

    ng = _buyer(db, "Nagpur Agro Traders")
    assert not ng["sufficient_history"] and ng["label"] == rep.LABEL_INSUFFICIENT
    assert _frac(ng, "pickup_reliability") == (2, 2)


def test_transport_profiles(seeded):
    db, _ = seeded
    s = _agency(db, "Shakti Logistics")
    assert [_frac(s, k) for k in ("on_time_pickup", "on_time_delivery", "quote_accuracy", "trip_fulfilment")] == \
        [(13, 14), (13, 14), (12, 14), (14, 14)]                   # rejected dispute: still counts

    b = _agency(db, "Bilaspur Roadways")
    assert [_frac(b, k) for k in ("on_time_pickup", "on_time_delivery", "quote_accuracy")] == [(10, 10), (9, 10), (10, 10)]

    mk = _agency(db, "Mahakoshal Carriers")
    assert mk["completed_outcomes"] == 6 and mk["trip_history"]["contested_items_under_review"] == 1
    assert [_frac(mk, k) for k in ("on_time_pickup", "on_time_delivery", "quote_accuracy")] == [(4, 6), (4, 6), (3, 6)]

    cl = _agency(db, "Chhattisgarh Cargo Link")
    assert _frac(cl, "on_time_delivery") is None and _frac(cl, "quote_accuracy") == (7, 8)

    ra = _agency(db, "Rapid Agri Haulers")
    assert _frac(ra, "trip_fulfilment") == (5, 7)
    assert ra["trip_history"]["cancelled_by_agency"] == 2 and ra["trip_history"]["cancelled_other_or_unrecorded"] == 2

    vm = _agency(db, "Vidarbha Movers")
    assert not vm["sufficient_history"] and _frac(vm, "quote_accuracy") == (1, 1)


def test_ranking_leaves_new_partners_unranked(seeded):
    db, _ = seeded
    ids = [t.id for t in db.query(models.Transporter).all()]
    ranked = rep.rank_profiles([rep.transporter_profile(db, i, NOW) for i in ids])
    names = [p["name"] for p in ranked]
    assert names[-1] == "Vidarbha Movers" and ranked[-1]["ranking"]["position"] is None
    assert all(p["ranking"]["position"] for p in ranked[:-1])


def test_every_dispute_status_is_present(seeded):
    db, _ = seeded
    statuses = {d.status for d in db.query(models.ReputationDispute).all()}
    assert statuses == {"OPEN", "UNDER_REVIEW", "UPHELD", "REJECTED"}


def test_seed_refuses_to_run_twice_and_reset_removes_everything(seeded):
    db, manifest = seeded
    with pytest.raises(RuntimeError):
        seed_mod.seed(db, NOW)
    seed_mod.reset(db, manifest)
    for model in (models.Transporter, models.TransportRequest, models.PerformanceRecord,
                  models.ReputationDispute, models.Transaction, models.Buyer):
        assert db.query(model).count() == 0
