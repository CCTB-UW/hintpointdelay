from pathlib import Path

from CTFd.cache import clear_standings
from CTFd.models import Hints, db
from CTFd.schemas.awards import AwardSchema
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
