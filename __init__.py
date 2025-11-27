
from flask import Blueprint, render_template, request

from CTFd.cache import clear_standings
from CTFd.constants.languages import SELECT_LANGUAGE_LIST
from CTFd.models import Hints, Unlocks, db, get_class_by_tablename
from CTFd.plugins.LuaUtils import ConfigPanel, _LuaAsset
from CTFd.schemas.awards import AwardSchema
from CTFd.schemas.unlocks import UnlockSchema
from CTFd.utils import get_config
from CTFd.utils.decorators import (
    admins_only,
    authed_only,
    during_ctf_time_only,
    require_verified_emails,
)
from CTFd.utils.user import get_current_user


class DelayedHints(db.Model):
    __tablename__ = "delayedhints"
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    hint = db.Column(
        db.Integer, db.ForeignKey("hints.id", ondelete="CASCADE", onupdate="CASCADE")
    )

    def __init__(self, user, hint):
        self.user = user.id
        self.hint = hint.id
        self.challenge = hint.challenge_id


hintpoint = Blueprint(
    "hintpointdelay",
    __name__,
    template_folder="templates",
    static_folder="staticAssets",
)

def load(app):
    app.db.create_all()

    app.jinja_env.globals.update(hintpointassets=_LuaAsset("hintpointdelay"))
    app.register_blueprint(hintpoint, url_prefix="/hintpointdelay")

    def get_modified_challenge_points(challenge):
        user = get_current_user()
        hintids = DelayedHints.query.filter(
                DelayedHints.challenge == challenge.id,
                DelayedHints.user == user.id,
            ).all()
        
        score = challenge.value
        if hintids:
            for hid in hintids:
                hint = Hints.query.filter(
                            Hints.id== hid,
                        ).first()
                score -= hint.cost
        
        return score
    
    def apply_delayed_hints(challenge):
        user = get_current_user()
        hintids = DelayedHints.query.filter(
                DelayedHints.challenge == challenge.id,
                DelayedHints.user == user.id,
            ).all()

        if hintids:
            for hid in hintids:
                hint = Hints.query.filter(
                            Hints.id== hid,
                        ).first()
                if hint:
                    name = hint.name
                    description = hint.description
                    category = hint.category
                    user_id = user.id
                    user_awards = user.awards

                    for award in user_awards:
                        if award.cost == 0 and award.name == name and award.description == description and award.category == category and (award.user_id == user_id or award.team_id == user.team_id):
                            #delete old award
                            db.session.delete(award)

                            #create new award with cost
                            award_schema = AwardSchema()
                            new_award = {
                                "user_id": user.id,
                                "team_id": user.team_id,
                                "name": hint.name,
                                "description": hint.description,
                                "value": (-hint.cost),
                                "category": hint.category,
                            }

                            new_award = award_schema.load(new_award)
                            db.session.add(new_award.data)
                            
                    db.session.commit()
                    db.session.close()
                    clear_standings()        


    @app.route("/admin/hintpointdelay")
    @admins_only
    def hintpoint_config():
        standard = get_config("inlineTranslationStandard")
        configs = [
            ConfigPanel(
                "Standard Language",
                "Set the standard language.",
                standard,
                "inlineTranslationStandard",
                SELECT_LANGUAGE_LIST,
            )
        ]
        return render_template("hintconfig.html", configs=configs)

    @during_ctf_time_only
    @require_verified_emails
    @authed_only
    def post(self):
        req = request.get_json()
        user = get_current_user()

        target_type = req["type"]

        req["user_id"] = user.id
        req["team_id"] = user.team_id

        Model = get_class_by_tablename(req["type"])
        target = Model.query.filter_by(id=req["target"]).first_or_404()

        if target_type == "hints":
            # We should use the team's score if in teams mode
            # user.account gives the appropriate account based on team mode
            # Use get_score with admin to get the account's full score value
            if target.cost > user.account.get_score(admin=True):
                return (
                    {
                        "success": False,
                        "errors": {
                            "score": "You do not have enough points to unlock this hint"
                        },
                    },
                    400,
                )

            schema = UnlockSchema()
            response = schema.load(req, session=db.session)

            if response.errors:
                return {"success": False, "errors": response.errors}, 400

            # Search for an existing unlock that matches the target and type
            # And matches either the requesting user id or the requesting team id
            existing = Unlocks.query.filter(
                Unlocks.target == req["target"],
                Unlocks.type == req["type"],
                Unlocks.account_id == user.account_id,
            ).first()
            if existing:
                return (
                    {
                        "success": False,
                        "errors": {"target": "You've already unlocked this target"},
                    },
                    400,
                )

            db.session.add(response.data)

            award_schema = AwardSchema()
            award = {
                "user_id": user.id,
                "team_id": user.team_id,
                "name": target.name,
                "description": target.description,
                "value": (-target.cost),
                "category": target.category,
            }

            award = award_schema.load(award)
            db.session.add(award.data)
            db.session.commit()
            clear_standings()

            response = schema.dump(response.data)

            return {"success": True, "data": response.data}
        elif target_type == "solutions":
            schema = UnlockSchema()
            response = schema.load(req, session=db.session)

            if response.errors:
                return {"success": False, "errors": response.errors}, 400

            # Search for an existing unlock that matches the target and type
            # And matches either the requesting user id or the requesting team id
            existing = Unlocks.query.filter(
                Unlocks.target == req["target"],
                Unlocks.type == req["type"],
                Unlocks.account_id == user.account_id,
            ).first()
            if existing:
                return (
                    {
                        "success": False,
                        "errors": {"target": "You've already unlocked this target"},
                    },
                    400,
                )

            db.session.add(response.data)
            db.session.commit()

            response = schema.dump(response.data)

            return {"success": True, "data": response.data}
        else:
            return (
                {
                    "success": False,
                    "errors": {"type": "Unknown target type"},
                },
                400,
            )

