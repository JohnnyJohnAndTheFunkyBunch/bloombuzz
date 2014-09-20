<!DOCTYPE html>
<html>
<link rel="stylesheet" type="text/css" href="http://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
<script src="http://ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js"></script>
<script src="http://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
<style>
    .panel {
        margin-bottom:10px;
    }
    .jma {
        float:right;
    }
    p {
        width: 200px;
    }
    .panel-title {
        padding-top:8px;
    }
</style>
<body>
    <nav class="navbar navbar-default" role="navigation">
      <div class="container-fluid">

    <div class="navbar-header">
      <a class="navbar-brand" href="">BloomBuzz</a>
    </div>
        <!-- Collect the nav links, forms, and other content for toggling -->
        <div class="collapse navbar-collapse" id="bs-example-navbar-collapse-1">
          <form class="navbar-form navbar-left">
            <div class="form-group">
              <input id="ticker" type="text" class="form-control" placeholder="Ticker">
            </div>
             <select id="type" class="form-control">
                <option>Above</option>
                <option>Below</option>
              </select>
              <input id="price" type="text" class="form-control" placeholder="Price">
            <button id="submit" type="submit" class="btn btn-default">Submit</button>
          </form>
          <ul class="nav navbar-nav navbar-right">
             <li><a href=""><?php echo $_GET['s']?></a></li>
          </ul>
        </div><!-- /.navbar-collapse -->
      </div><!-- /.container-fluid -->
    </nav>
    <div class="container-fluid SW-container"> 
        <!-- dynamic content here -->
        <!-- end dynamic content here -->
    <div>    
</body>
<script>
    var key = '<?php echo $_GET['s']?>';
    var host = "ws://54.68.142.188:9876";
    var SWContainer = $('.SW-container');
    var submitButton = $('#submit');
    var tickerInput = $('#ticker');
    var priceInput = $('#price');
    var typeInput = $('#type');
    console.log("Host:", host);
    
    var s = new WebSocket(host);
    
    s.onopen = function (e) {
        console.log("Socket opened.");
        s.send("key,"+key);
    };
    
    s.onclose = function (e) {
        console.log("Socket closed.");
    };
    
    s.onmessage = function (e) {
        console.log(e.data);
        var msg = e.data;
        var msgArray = msg.split(',');
        if (msgArray[0] == "set") {
            var ticker = msgArray[1];
            var typeNum = msgArray[2];
            var type = "";
            if (typeNum == -1) {
                type = "Below";
            }
            else if (typeNum == 1) {
                type = "Above";
            }
            var price = parseFloat(msgArray[3]);
            var trig = parseInt(msgArray[4]);
            addSW(ticker, type, price, trig);
        }
        else if (msgArray[0] == "trg") {
            $('#'+msgArray[1]).removeClass("panel-primary panel-info").addClass("panel-danger"); 
        }
    };
    
    s.onerror = function (e) {
        console.log("Socket error:", e);
    };

    submitButton.click(function() {
        var ticker = tickerInput.val();
        var price = parseFloat(priceInput.val());
        var type = typeInput.val();
        var typeNum;
        if (type == "Above") {
            typeNum = 1;
        }
        else if (type == "Below") {
            typeNum = -1;
        }
        var msg = "set," + key + "," + ticker + "," + typeNum + "," + price.toFixed(2);
        console.log(msg);
        s.send(msg)
        addSW(ticker, type, price, 0)
    });
    function addSW(ticker, type, price, trig) {
        if (trig == 0) {
            if (type == "Above"){
                SWContainer.append(
            '<div id="'+ticker+"1"+(price * 100).toString()+'"class="panel panel-info">' +
                '<div class="panel-heading clearfix">' +
                    '<h4 class="panel-title pull-left">' +
                    ticker + ' ' + type + ' ' + price.toFixed(2) + '</h4>'+
                    '<div class="btn-group pull-right">'+
                        '<a class="btn btn-default ack">Acknowledge</a>'+
                        '<a class="btn btn-default resolved">Resolved</a>'+
                        '<a class="btn btn-default delete">Delete</a>'+
                    '</div>'+
                '</div>'+
            '</div>')
            }
            else {
                SWContainer.append(
            '<div id="'+ticker+"-1"+(price * 100).toString()+'"class="panel panel-primary">' +
                '<div class="panel-heading clearfix">' +
                    '<h4 class="panel-title pull-left">' +
                    ticker + ' ' + type + ' ' + price.toFixed(2) + '</h4>'+
                    '<div class="btn-group pull-right">'+
                        '<a class="btn btn-default ack">Acknowledge</a>'+
                        '<a class="btn btn-default resolved">Resolved</a>'+
                        '<a class="btn btn-default delete">Delete</a>'+
                    '</div>'+
                '</div>'+
            '</div>')
            }
        }
        else if (trig == 1) {
                SWContainer.append(
            '<div id="'+ticker+"-1"+(price * 100).toString()+'"class="panel panel-danger">' +
                '<div class="panel-heading clearfix">' +
                    '<h4 class="panel-title pull-left">' +
                    ticker + ' ' + type + ' ' + price.toFixed(2) + '</h4>'+
                    '<div class="btn-group pull-right">'+
                        '<a class="btn btn-default ack">Acknowledge</a>'+
                        '<a class="btn btn-default resolved">Resolved</a>'+
                        '<a class="btn btn-default delete">Delete</a>'+
                    '</div>'+
                '</div>'+
            '</div>')
        }
        $(".resolved").click(function() {
            var panel = $(this).parent().parent().parent();
            var myId = panel.attr("id");
            var index = myId.indexOf('-');
            if (index == -1) {
                panel.removeClass('panel-danger').addClass('panel-info')
            }
            else {
                panel.removeClass('panel-danger').addClass('panel-primary')
            }
            s.send("res," + key + "," +myId);
        });
        $(".delete").click(function() {
            // get ticker type price
            var panel = $(this).parent().parent().parent();
            var myId = panel.attr("id");
            panel.remove();
            s.send("del," + key +"," + myId);
        });
        $(".ack").click(function() {
            // get ticker type price
            var panel = $(this).parent().parent().parent();
            var myId = panel.attr("id");
            var index = myId.indexOf('-');
            if (index == -1) {
                panel.removeClass('panel-danger').addClass('panel-warning')
            }
            else {
                panel.removeClass('panel-danger').addClass('panel-warning')
            var panel = $(this).parent().parent().parent();

            var myId = panel.attr("id");
            panel.remove();
            }
            s.send("ack," + key +"," + myId);
        });
    }


</script>
</html>
