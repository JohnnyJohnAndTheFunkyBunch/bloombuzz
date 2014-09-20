<!DOCTYPE html>
<html>
<link rel="stylesheet" type="text/css" href="http://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css">
<link rel="stylesheet" type="text/css" href="main.css">
<script src="http://ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js"></script>
<body>
    <div class="alert alert-success connection" role="alert">Connected</div>
    <div class="alert alert-warning connection" role="alert">Connecting...</div>
    <div class="alert alert-danger connection" role="alert" style="display:none">Disconnected</div>
    <div class="container-fluid header">
        <div class="row">
            <div class="col-md-1">
                <button type="button" class="btn btn-default" id="mainmenu"> Main Menu </button>
            </div>
            <div class="col-md-3">
                <div class="input-group">
                    <input type="text" class="form-control" placeholder="Username">
                    <div class="input-group-btn">
                        <button type="button"  class="btn btn-default">Change Name</button>
                    </div>
                </div>
            </div>
            <div class="col-md-4"></div> 
            <div class="col-md-4">Link: http://jonathan.ma/session.php?s=<?php echo $_GET['s']?></div>
        </div>
    </div>
    <div class="container-fluid main">
        <div class="row">
            <div class="col-md-9 content">
                <!-- Start Dynamic Content -->


                <!-- End Dynamic Content -->
            </div>
            <div class="col-md-3 side">
                <div class="player-box"> </div>
                <div class="console-box"> </div>
            </div> 
        </div>
    </div>
</body>
<script src="http://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"></script>
<script>
var session = '<?php echo $_GET['s']?>';
</script>
<script src="main.js"></script>

</html>
