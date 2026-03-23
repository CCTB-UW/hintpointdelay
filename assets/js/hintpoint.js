import $ from "jquery";

window.Alpine.data("Hintpoints",()=>({                    

    idx: 0,
    challengevalue: '',
    async hintpointvalue(id){
        const url = `/api/hintpoint/challengevalue/${id}`;
        const res = await $.get(url);
        this.challengevalue = res.data;
        this.idx = id;
    }
}))

//challenge view
const observer = new MutationObserver(callback);
const woppy = $("#challenge-window")[0];
if (woppy) {
    observer.observe(woppy,{attributes: true});
}


window.Alpine.start()