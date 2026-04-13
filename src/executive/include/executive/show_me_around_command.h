#pragma once

#include "executive/high_level_command.h"
#include <algorithm>
#include <vector>

namespace executive {

class ShowMeAroundCommand : public HighLevelCommand {
public:
    explicit ShowMeAroundCommand(ExecutionContext ctx)
        : HighLevelCommand(std::move(ctx))
    {}

    std::string get_name() const override { return "show_me_around"; }

    void configure(const std::vector<Landmark>& landmarks) override {
        landmarks_ = landmarks;
    }

    bool execute(ProgressCallback on_progress) override {
        status_ = CommandStatus::IN_EXECUTION;

        sort_by_distance(ctx_.home);

        on_progress("ShowMeAround: visiting " + std::to_string(landmarks_.size()) +
                    " landmarks in optimized order.");

        for (size_t i = 0; i < landmarks_.size(); ++i) {
            const auto& lm = landmarks_[i];

            on_progress("Visiting landmark " + std::to_string(i + 1) + "/" +
                        std::to_string(landmarks_.size()) + ": " + lm.name);

            if (!navigate_to(lm.position, on_progress, lm.name)) {
                status_ = CommandStatus::FAILED;
                return false;
            }

            if (!wait(on_progress)) {
                status_ = CommandStatus::FAILED;
                return false;
            }
        }

        status_ = CommandStatus::NAVIGATING_HOME;
        on_progress("All landmarks visited. Returning home.");

        if (!navigate_to(ctx_.home, on_progress, "home")) {
            status_ = CommandStatus::FAILED;
            return false;
        }

        status_ = CommandStatus::COMPLETED;
        on_progress("ShowMeAround completed.");
        return true;
    }

private:
    void sort_by_distance(const Position& start) {
        std::vector<Landmark> sorted;
        sorted.reserve(landmarks_.size());
        auto remaining = landmarks_;
        Position current = start;

        while (!remaining.empty()) {
            auto nearest = std::min_element(remaining.begin(), remaining.end(),
                [&current](const Landmark& a, const Landmark& b) {
                    return current.distance_to(a.position) < current.distance_to(b.position);
                });

            current = nearest->position;
            sorted.push_back(std::move(*nearest));
            remaining.erase(nearest);
        }

        landmarks_ = std::move(sorted);
    }

    std::vector<Landmark> landmarks_;
};

}  // namespace executive
