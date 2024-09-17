from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CurrentLeague(BaseModel):
    leagueId: int
    title: str
    requiredNumberOfPointsToAchieve: int
    bonusPoints: int
    miningSpeed: int
    iconName: str
    status: str


class UserData(BaseModel):
    id: int
    username: str
    telegramId: str
    pointsCount: int
    referralCode: str
    referralId: int | None
    lastReferralPointsClaimDate: datetime
    dailyBonusStreakCount: int
    lastDailyBonusClaimDate: Optional[datetime] = None
    lastMiningBonusClaimDate: datetime
    lastDailyCheckInClaimDate: Optional[datetime] = None
    miningBoostCount: int
    walletAddress: Optional[str] = None
    isWalletConnected: bool
    isWalletSigned: bool
    isWalletSignLoading: bool
    currentLeague: CurrentLeague
