import $ from "jquery";

window.Alpine.data("Hintpoints",()=>({                    

    idx: 0,
    challengevalue: '',
    async hintpointvalue(id){
        const url = `/api/hintpoint/challengevalue/${id}`;
        const res = await $.get(url);
        this.challengevalue = res.data;
        this.idx = id;
    },
    refreshValue() {
        if (this.idx) {
            this.hintpointvalue(this.idx);
        }
    },
    init() {
        // Listen for refresh events from other components
        window.addEventListener('refreshAllHints', () => {
            this.refreshValue();
        });
    }
}))


window.Alpine.start()