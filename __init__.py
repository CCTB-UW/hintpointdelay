
from pathlib import Path

from flask import Blueprint, render_template, request

from CTFd.cache import clear_standings
from CTFd.models import Challenges, Hints, db, get_class_by_tablename
from CTFd.plugins.LuaUtils import ConfigPanel, _LuaAsset, run_after_route
from CTFd.schemas.awards import AwardSchema
from CTFd.utils import get_config
from CTFd.utils.decorators import admins_only
from CTFd.utils.logging import log
from CTFd.utils.plugins import override_template
from CTFd.utils.user import get_current_user


def registerTemplate(old_path, new_path):
    dir_path = Path(__file__).parent.resolve()
    template_path = dir_path / "templates" / new_path
    override_template(old_path, open(template_path).read())

class DelayedHints(db.Model):
    __tablename__ = "delayedhints"
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    hint = db.Column(
        db.Integer, db.ForeignKey("hints.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    challenge = db.Column(db.Integer, db.ForeignKey("challenges.id", ondelete = "CASCADE", onupdate="CASCADE"))

    def __init__(self, user, hint):
        self.user = user.id
        self.hint = hint.id
        self.challenge = hint.challenge_id

def get_modified_challenge_points(challenge_id,challenge_value):
        user = get_current_user()
        try:
            hintids = DelayedHints.query.filter(
                    DelayedHints.challenge == challenge_id,
                    DelayedHints.user == user.id,
                ).all()
        except():
            hintids = False
        
        score = challenge_value
        if hintids:
            for hid in hintids:
                hint = Hints.query.filter(
                            Hints.id== hid.hint,
                        ).first()
                score -= hint.cost
        
        return score
    
def apply_delayed_hints(challenge_id):
    user = get_current_user()
    try:
        hintids = DelayedHints.query.filter(
                DelayedHints.challenge == challenge_id,
                DelayedHints.user == user.id,
            ).all()
    except():
        hintids = False
    if hintids:
        for hid in hintids:
            
            hint = Hints.query.filter(
                        Hints.id == hid.hint,
                    ).first()
            if hint:
                name = hint.name
                description = hint.description
                category = hint.category
                user_id = user.id
                user_awards = user.awards

                for award in user_awards:
                    if award.value == 0 and award.name == name and award.description == description and award.category == category and (award.user_id == user_id or award.team_id == user.team_id):
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
                        break
                
                db.session.commit()
                db.session.close()
                clear_standings()        

def isSolved(challenge_id):
    user = get_current_user()
    solved = user.solves
    for solve in solved:
        if solve.challenge_id == challenge_id:
            return True
    return False

hintpoint = Blueprint(
    "hintpointdelay",
    __name__,
    template_folder="templates",
    static_folder="staticAssets",
)

def load(app):
    
    app.db.create_all()

    #jinja globals 
    app.jinja_env.globals.update(hintpointvalue=get_modified_challenge_points)
    app.jinja_env.globals.update(hintpointassets=_LuaAsset("hintpointdelay"))
    app.register_blueprint(hintpoint, url_prefix="/hintpointdelay")

    registerTemplate("challenge.html","hintchallenge.html")
    registerTemplate("challenges.html","hintchallenges.html")

    #config page    
    @app.route("/admin/hintpointdelay")
    @admins_only
    def hintpoint_config():
        standard = get_config("hintpointdelay")
        if standard:
            standard = "enabled"
        else:
            standard = "disabled"

        configs = [
            ConfigPanel(
                "Delayed Hints",
                "Toggles delayed hints, making it so hint cost is subtracted from challenge value instead of user.",
                standard,
                "hintpointdelay"
            )
        ]
        return render_template("hintconfig.html", configs=configs)

    @app.route("/api/hintpoint/challengevalue/<challenge_id>",methods=['GET'])
    def get_hint_Values(challenge_id):
        try:
            challenge = Challenges.query.filter(
                    Challenges.id == challenge_id
                ).first()
        except():
            return {"success": False, "status":500}
        res = get_modified_challenge_points(challenge_id,challenge.value)
        return {"success": True, "data":res}

    #modified award unlock
    def modify_award(res):
        req = request.get_json()
        award_data = res[0].get_json()
        if not award_data['success']:
            return
        
        user = get_current_user()

        Model = get_class_by_tablename(req["type"])
        target = Model.query.filter_by(id=req["target"]).first_or_404()
        
        # replace costly hint with non cost hint if not solved

        if(req["type"] == "hints" and not isSolved(target.challenge_id)):
            hint = target
            name = hint.name
            description = hint.description
            category = hint.category
            user_id = user.id
            user_awards = user.awards

            for award in user_awards:
                if award.value != 0 and award.name == name and award.description == description and award.category == category and (award.user_id == user_id or award.team_id == user.team_id):
                    #delete old award
                    db.session.delete(award)

                    #create new award with cost
                    award_schema = AwardSchema()
                    new_award = {
                        "user_id": user.id,
                        "team_id": user.team_id,
                        "name": hint.name,
                        "description": hint.description,
                        "value": (0),
                        "category": hint.category,
                    }

                    new_award = award_schema.load(new_award)
                    db.session.add(new_award.data)

                    delayedhint = DelayedHints(user,hint)
                    db.session.add(delayedhint)
                    break

            db.session.commit()
            clear_standings()


    run_after_route(app,'api.unlocks_unlock_list',modify_award)

    def modify_challenge_correct(res):
        response = res[0].get_json()
        if (response['success'] and response['data']['status'] == 'correct'):
            if not request.is_json:
                request_data = request.form
            else:
                request_data = request.get_json()

            challenge_id = request_data.get("challenge_id")
            apply_delayed_hints(challenge_id)

    run_after_route(app,'api.challenges_challenge_attempt',modify_challenge_correct)