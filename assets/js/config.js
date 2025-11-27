import $ from "jquery";
import CTFd from "./index";

$(".toggle-button").click(function() {
    function foo (res) {
        $("#"+res.id).html(res.data)
        if(res.data === "enabled"){
            $("#"+res.id).removeClass("bg-danger").addClass("bg-success")
        }else{
            $("#"+res.id).removeClass("bg-success").addClass("bg-danger")
        }}
    $.get(`/admin/inlineTranslation/config/${this.id}`,function(res){
        foo(res)
    })
  });

$("select").on('change',function(){
    CTFd.fetch(`/admin/inlineTranslation/config/${this.id}`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        value: this.value
      }),
    })  
});