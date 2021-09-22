pragma solidity ^0.5.0;

import "./PupperCoin.sol";
import "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/release-v2.5.0/contracts/crowdsale/Crowdsale.sol";
import "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/release-v2.5.0/contracts/crowdsale/emission/MintedCrowdsale.sol";
import "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/release-v2.5.0/contracts/crowdsale/validation/CappedCrowdsale.sol";
import "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/release-v2.5.0/contracts/crowdsale/validation/TimedCrowdsale.sol";
import "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/release-v2.5.0/contracts/crowdsale/distribution/RefundablePostDeliveryCrowdsale.sol";

//Inherit the crowdsale contracts
contract PupperCoinSale is Crowdsale, MintedCrowdsale, CappedCrowdsale, TimedCrowdsale, RefundablePostDeliveryCrowdsale {

    constructor(
        address payable wallet,
        uint goal,
        uint rate,
        PupperCoin token,
        uint OpenTime,
        uint CloseTime
        )
    
        Crowdsale(rate, wallet, token)
        MintedCrowdsale()
        CappedCrowdsale(goal)
        TimedCrowdsale(OpenTime, CloseTime)
        RefundableCrowdsale(goal)
        RefundablePostDeliveryCrowdsale()
            
        public
    {
        // constructor can stay empty
    }
}


contract PupperCoinSaleDeployer {

    address public token_sale_address;
    address public token_address;

    constructor(
        string memory name,
        string memory symbol,
        address payable wallet
    )
        public
    {
        // create the PupperCoin and keep its address handy
            PupperCoin token = new PupperCoin(name, symbol, 0);
            token_address = address(token);
            
        // create the PupperCoinSale and tell it about the token, set the goal, and set the open and close times to now and now + 24 weeks.    
            uint goal = 300 ether;
            uint OpenTime = now;
            uint CloseTime = now + 24 weeks;
            
            PupperCoinSale pupper_sale = new PupperCoinSale(wallet, goal, 1, token, OpenTime, CloseTime);
            token_sale_address = address(pupper_sale);

        
        // make the PupperCoinSale contract a minter, then have the PupperCoinSaleDeployer renounce its minter role
            token.addMinter(token_sale_address);
            token.renounceMinter();
    }
}
