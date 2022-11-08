<?php

use App\Routes;

?>
<div class="row home">
    <div class="col">
        <h2>Mission</h2>
        <p>
            Welcome to the <?= PLANT_NAME ?> recycling factory. We are dedicated to squeezing every 
            little remaining value out of electronic junk to help you and our society. Every little 
            thing helps. Look around your place for unused equipment, and we will give them a second
            and more useful life.
        </p>
    </div>
    <div class="col">
        <h2>E-Waste Recycle</h2>
        <p>
            Register your items right now to drop off your valuable waste at our location without 
            any further paperwork.
        </p>
        <a class="button" href="<?=Routes::RECYCLE_PHYSICAL_REGISTER?>">Item registration</a>
    </div>

    <div class="col">
        <h2>Digital Processing</h2>
        <p>
            We also recycle information from digital archives. Simply upload the data to our waste 
            data aggregation endpoint, and we will use the extracted information to move our
            community further by scanning your archives using our advanced data recycling
            algorithms. Are you interested in your findings? Create an account with your first
            upload.
        </p>
        <a class="button" href="<?=Routes::RECYCLE_DIGITAL_REGISTER?>">Upload form</a>
    </div>
</div>